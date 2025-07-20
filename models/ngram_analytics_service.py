"""
NGramAnalyticsService for advanced n-gram performance analysis.

This module provides comprehensive analytics for n-gram performance including:
- Decaying average calculations for recent performance weighting
- Performance summaries with historical tracking
- Heatmap data generation for visualization
- Migration of analytics methods from NGramManager
"""

import logging
import uuid
from datetime import datetime
from math import log
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from db.database_manager import DatabaseManager
from models.ngram_manager import NGramManager

logger = logging.getLogger(__name__)


class DecayingAverageCalculator:
    """
    Calculator for decaying average with exponential weighting.

    Implements an ELO-like system where more recent measurements
    have exponentially higher weights than older ones.
    """

    def __init__(self, decay_factor: float = 0.9, max_samples: int = 20) -> None:
        """
        Initialize the decaying average calculator.

        Args:
            decay_factor: Exponential decay factor (0.0 to 1.0). Higher values
                         give more weight to recent measurements.
            max_samples: Maximum number of most recent samples to consider.
        """
        self.decay_factor = decay_factor
        self.max_samples = max_samples

    def calculate_decaying_average(self, values: List[float], timestamps: List[datetime]) -> float:
        """
        Calculate decaying average with exponential weighting.

        More recent values receive exponentially higher weights according to:
        weight = decay_factor ^ (days_ago)

        Args:
            values: List of measurement values
            timestamps: List of corresponding timestamps (must match values length)

        Returns:
            Weighted average with recent values weighted more heavily
        """
        if not values or not timestamps:
            return 0.0

        if len(values) != len(timestamps):
            raise ValueError("Values and timestamps must have the same length")

        # Sort by timestamp descending and take only the most recent max_samples
        recent_data = sorted(zip(timestamps, values, strict=True), reverse=True)[: self.max_samples]

        if not recent_data:
            return 0.0

        if len(recent_data) == 1:
            return recent_data[0][1]

        # Calculate weights based on days from most recent
        most_recent_time = recent_data[0][0]  # Now this is actually the most recent
        weighted_sum = 0.0
        weight_sum = 0.0

        for timestamp, value in recent_data:
            days_ago = (most_recent_time - timestamp).total_seconds() / (24 * 3600)
            weight = self.decay_factor ** max(0, days_ago)
            weighted_sum += value * weight
            weight_sum += weight

        return weighted_sum / weight_sum if weight_sum > 0 else 0.0


class NGramPerformanceData(BaseModel):
    """Data model for n-gram performance metrics."""

    ngram_text: str = Field(..., min_length=1, max_length=50)
    ngram_size: int = Field(..., ge=1, le=20)
    decaying_average_ms: float = Field(..., ge=0.0)
    target_performance_pct: float = Field(..., ge=0.0, le=100.0)
    sample_count: int = Field(..., ge=0)
    last_measured: Optional[datetime] = None
    performance_category: str = Field(..., pattern="^(green|amber|grey)$")

    model_config = {"extra": "forbid"}


class NGramHeatmapData(BaseModel):
    """Data model for n-gram heatmap visualization."""

    ngram_text: str = Field(..., min_length=1, max_length=50)
    ngram_size: int = Field(..., ge=1, le=20)
    decaying_average_ms: float = Field(..., ge=0.0)
    decaying_average_wpm: float = Field(..., ge=0.0)
    target_performance_pct: float = Field(..., ge=0.0, le=100.0)
    sample_count: int = Field(..., ge=0)
    last_measured: Optional[datetime] = None
    performance_category: str = Field(..., pattern="^(green|amber|grey)$")
    color_code: str = Field(..., pattern="^#[0-9A-Fa-f]{6}$")

    model_config = {"extra": "forbid"}


class NGramHistoricalData(BaseModel):
    """Data model for historical n-gram performance tracking."""

    ngram_text: str = Field(..., min_length=1, max_length=50)
    ngram_size: int = Field(..., ge=1, le=20)
    measurement_date: datetime
    decaying_average_ms: float = Field(..., ge=0.0)
    sample_count: int = Field(..., ge=0)

    model_config = {"extra": "forbid"}


class NGramSummaryData(BaseModel):
    """Data model for n-gram summary statistics."""

    summary_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    keyboard_id: str = Field(..., min_length=1)
    ngram_text: str = Field(..., min_length=1, max_length=50)
    ngram_size: int = Field(..., ge=1, le=20)
    decaying_average_ms: float = Field(..., ge=0.0)
    target_speed_ms: float = Field(..., ge=0.0)
    target_performance_pct: float = Field(..., ge=0.0, le=100.0)
    meets_target: bool
    sample_count: int = Field(..., ge=0)
    last_updated: datetime
    created_at: datetime

    model_config = {"extra": "forbid"}


class NGramStats:
    """Data class to hold n-gram statistics for compatibility."""

    ngram: str
    ngram_size: int
    avg_speed: float  # in ms per keystroke
    total_occurrences: int
    ngram_score: float
    last_used: Optional[datetime]


class NGramAnalyticsService:
    """
    Service for advanced n-gram performance analytics.

    Provides comprehensive analytics including decaying averages,
    performance summaries, heatmap data, and historical tracking.
    """

    def __init__(self, db: DatabaseManager, ngram_manager: NGramManager) -> None:
        """
        Initialize the NGramAnalyticsService with database and
        n-gram manager dependencies.
        """
        self.db = db
        self.ngram_manager = ngram_manager
        self.decaying_average_calculator = DecayingAverageCalculator()

    def refresh_speed_summaries(self, user_id: str, keyboard_id: str) -> None:
        """
        Refresh cached speed summaries for a user and keyboard.

        Recalculates decaying averages and performance metrics from
        raw session data and updates the summary table.

        Args:
            user_id: User ID to refresh summaries for
            keyboard_id: Keyboard ID to refresh summaries for
        """
        if not self.db:
            logger.warning("No database connection for summary refresh")
            return

        try:
            # Get target speed for this keyboard
            keyboard_data = self.db.fetchone(
                "SELECT target_ms_per_keystroke FROM keyboards WHERE keyboard_id = ?",
                (keyboard_id,),
            )

            if not keyboard_data:
                logger.warning(f"No keyboard found with ID: {keyboard_id}")
                return

            target_speed_ms = keyboard_data["target_ms_per_keystroke"]

            # Get all unique n-grams for this user/keyboard from recent sessions
            query = """
                WITH recent_sessions AS (
                    SELECT session_id, start_time
                    FROM practice_sessions
                    WHERE user_id = ? AND keyboard_id = ? 
                    ORDER BY start_time DESC
                    LIMIT 100
                ),
                ngram_data AS (
                    SELECT 
                        ngram_text,
                        ngram_size,
                        ms_per_keystroke,
                        rs.start_time
                    FROM session_ngram_speed ngram
                    INNER JOIN recent_sessions rs ON ngram.session_id = rs.session_id
                    ORDER BY rs.start_time DESC
                )
                SELECT 
                    ngram_text,
                    ngram_size,
                    GROUP_CONCAT(ms_per_keystroke, ',') as speeds,
                    GROUP_CONCAT(start_time, ',') as timestamps,
                    COUNT(*) as sample_count
                FROM ngram_data
                GROUP BY ngram_text, ngram_size
            """

            ngram_results = self.db.fetchall(query, (user_id, keyboard_id))

            # Process each n-gram
            for row in ngram_results:
                ngram_text = row["ngram_text"]
                ngram_size = row["ngram_size"]
                speeds_str = row["speeds"]
                timestamps_str = row["timestamps"]
                sample_count = row["sample_count"]

                # Parse speeds and timestamps
                speeds = [float(s) for s in speeds_str.split(",")]
                timestamps = [datetime.fromisoformat(t) for t in timestamps_str.split(",")]

                # Calculate decaying average
                decaying_avg = self.decaying_average_calculator.calculate_decaying_average(
                    speeds, timestamps
                )

                # Calculate performance percentage
                target_perf_pct = (
                    (target_speed_ms / decaying_avg * 100) if decaying_avg > 0 else 0.0
                )
                meets_target = decaying_avg <= target_speed_ms

                # Dual-insert: Insert into both current table and history table
                summary_id = str(uuid.uuid4())
                history_id = str(uuid.uuid4())
                now = datetime.now().isoformat()

                # Insert into current table (replace existing record)
                self.db.execute(
                    """
                    INSERT OR REPLACE INTO ngram_speed_summary_curr (
                        summary_id, user_id, keyboard_id, ngram_text, ngram_size,
                        decaying_average_ms, target_speed_ms, target_performance_pct,
                        meets_target, sample_count, updated_dt
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        summary_id,
                        user_id,
                        keyboard_id,
                        ngram_text,
                        ngram_size,
                        decaying_avg,
                        target_speed_ms,
                        target_perf_pct,
                        meets_target,
                        sample_count,
                        now,
                    ),
                )

                # Insert into history table for historical tracking
                self.db.execute(
                    """
                    INSERT INTO ngram_speed_summary_hist (
                        history_id, user_id, keyboard_id, ngram_text, ngram_size,
                        decaying_average_ms, target_speed_ms, target_performance_pct,
                        meets_target, sample_count, updated_dt
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        history_id,
                        user_id,
                        keyboard_id,
                        ngram_text,
                        ngram_size,
                        decaying_avg,
                        target_speed_ms,
                        target_perf_pct,
                        meets_target,
                        sample_count,
                        now,
                    ),
                )

            logger.info(f"Refreshed {len(ngram_results)} n-gram summaries for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to refresh speed summaries: {e}")

    def get_ngram_history(
        self, user_id: str, keyboard_id: str, ngram_text: str = None
    ) -> List[NGramHistoricalData]:
        """
        Retrieve historical performance data for n-grams.

        Args:
            user_id: User ID to get history for
            keyboard_id: Keyboard ID to get history for
            ngram_text: Optional filter for specific n-gram text

        Returns:
            List of NGramHistoricalData objects sorted by measurement date
        """
        if not self.db:
            logger.warning("No database connection for history retrieval")
            return []

        try:
            # Build query based on whether ngram_text filter is provided
            if ngram_text:
                query = """
                    SELECT 
                        user_id,
                        keyboard_id,
                        ngram_text,
                        ngram_size,
                        decaying_average_ms,
                        sample_count,
                        updated_dt
                    FROM ngram_speed_summary_hist 
                    WHERE user_id = ? AND keyboard_id = ? AND ngram_text = ?
                    ORDER BY updated_dt DESC
                """
                params = (user_id, keyboard_id, ngram_text)
            else:
                query = """
                    SELECT 
                        user_id,
                        keyboard_id,
                        ngram_text,
                        ngram_size,
                        decaying_average_ms,
                        sample_count,
                        updated_dt
                    FROM ngram_speed_summary_hist 
                    WHERE user_id = ? AND keyboard_id = ?
                    ORDER BY updated_dt DESC
                """
                params = (user_id, keyboard_id)

            results = self.db.fetchall(query, params)

            # Convert results to NGramHistoricalData objects
            history_data = []
            for row in results:
                history_data.append(
                    NGramHistoricalData(
                        user_id=row["user_id"],
                        keyboard_id=row["keyboard_id"],
                        ngram_text=row["ngram_text"],
                        ngram_size=row["ngram_size"],
                        decaying_average_ms=row["decaying_average_ms"],
                        sample_count=row["sample_count"],
                        measurement_date=datetime.fromisoformat(row["updated_dt"]),
                    )
                )

            logger.info(f"Retrieved {len(history_data)} historical records for user {user_id}")
            return history_data

        except Exception as e:
            logger.error(f"Failed to retrieve n-gram history: {e}")
            return []

    def get_speed_heatmap_data(
        self,
        user_id: str,
        keyboard_id: str,
        target_speed_ms: Optional[float] = None,
        ngram_size_filter: Optional[int] = None,
        exclude_successful: bool = False,
        sort_order: str = "worst_to_best",
    ) -> List[NGramHeatmapData]:
        """
        Get heatmap data for n-gram performance visualization.

        Args:
            user_id: User ID to get data for
            keyboard_id: Keyboard ID to get data for
            target_speed_ms: Optional target speed override
            ngram_size_filter: Optional filter for specific n-gram size
            exclude_successful: Whether to exclude n-grams meeting target
            sort_order: Sort order ("worst_to_best" or "best_to_worst")

        Returns:
            List of NGramHeatmapData objects for visualization
        """
        if not self.db:
            return []

        try:
            # Build query with filters
            conditions = ["user_id = ?", "keyboard_id = ?"]
            params = [user_id, keyboard_id]

            if ngram_size_filter:
                conditions.append("ngram_size = ?")
                params.append(ngram_size_filter)

            if exclude_successful:
                conditions.append("meets_target = 0")

            where_clause = " AND ".join(conditions)

            # Sort order
            sort_clause = (
                "decaying_average_ms DESC"
                if sort_order == "worst_to_best"
                else "decaying_average_ms ASC"
            )

            query = f"""
                SELECT 
                    ngram_text,
                    ngram_size,
                    decaying_average_ms,
                    target_speed_ms,
                    target_performance_pct,
                    meets_target,
                    sample_count,
                    last_updated
                FROM ngram_speed_summary_curr
                WHERE {where_clause}
                ORDER BY {sort_clause}
            """

            results = self.db.fetchall(query, tuple(params))

            heatmap_data = []
            for row in results:
                # Calculate WPM (assuming 5 chars per word)
                wpm = (
                    (60000 / row["decaying_average_ms"]) / 5
                    if row["decaying_average_ms"] > 0
                    else 0
                )

                # Determine color category and code
                if row["meets_target"]:
                    category = "green"
                    color_code = "#90EE90"  # Light green
                elif row["target_performance_pct"] >= 75.0:
                    category = "amber"
                    color_code = "#FFD700"  # Light amber
                else:
                    category = "grey"
                    color_code = "#D3D3D3"  # Light grey

                heatmap_data.append(
                    NGramHeatmapData(
                        ngram_text=row["ngram_text"],
                        ngram_size=row["ngram_size"],
                        decaying_average_ms=row["decaying_average_ms"],
                        decaying_average_wpm=wpm,
                        target_performance_pct=row["target_performance_pct"],
                        sample_count=row["sample_count"],
                        last_measured=datetime.fromisoformat(row["last_updated"]),
                        performance_category=category,
                        color_code=color_code,
                    )
                )

            return heatmap_data

        except Exception as e:
            logger.error(f"Failed to get heatmap data: {e}")
            return []

    def get_performance_trends(
        self, user_id: str, keyboard_id: str, time_window_days: int = 30
    ) -> Dict[str, List[NGramHistoricalData]]:
        """
        Get historical performance trends for n-grams.

        Analyzes how the decaying average performance has changed over time
        by calculating weighted averages at different time points.

        Args:
            user_id: User ID to get trends for
            keyboard_id: Keyboard ID to get trends for
            time_window_days: Number of days to look back

        Returns:
            Dictionary mapping n-gram text to list of historical data points
        """
        if not self.db:
            return {}

        try:
            # Get n-gram performance data over the specified time window
            query = """
                WITH time_series AS (
                    -- Generate a series of dates for the time window
                    WITH RECURSIVE date_series(date_val) AS (
                        SELECT DATE('now', '-' || ? || ' days')
                        UNION ALL
                        SELECT DATE(date_val, '+1 day')
                        FROM date_series
                        WHERE date_val < DATE('now')
                    )
                    SELECT date_val FROM date_series
                ),
                ngram_data AS (
                    -- Get n-gram speed data with timestamps
                    SELECT 
                        s.ngram_text,
                        s.ngram_size,
                        s.ngram_time_ms,
                        DATE(ps.start_time) as session_date,
                        ps.start_time,
                        ROW_NUMBER() OVER (
                            PARTITION BY s.ngram_text, s.ngram_size 
                            ORDER BY ps.start_time DESC
                        ) as recency_rank
                    FROM session_ngram_speed s
                    JOIN practice_sessions ps ON s.session_id = ps.session_id
                    WHERE ps.user_id = ? 
                        AND ps.keyboard_id = ?
                        AND ps.start_time >= DATE('now', '-' || ? || ' days')
                        AND s.ngram_time_ms > 0
                ),
                historical_points AS (
                    -- Calculate decaying average for each n-gram at each time point
                    SELECT 
                        ts.date_val as measurement_date,
                        nd.ngram_text,
                        nd.ngram_size,
                        COUNT(nd.ngram_time_ms) as sample_count,
                        -- Calculate decaying average using exponential weighting
                        CASE 
                            WHEN COUNT(nd.ngram_time_ms) > 0 THEN
                                SUM(
                                    nd.ngram_time_ms * 
                                    POWER(0.9, JULIANDAY(ts.date_val) - JULIANDAY(nd.session_date))
                                ) / SUM(
                                    POWER(0.9, JULIANDAY(ts.date_val) - JULIANDAY(nd.session_date))
                                )
                            ELSE 0
                        END as decaying_average_ms
                    FROM time_series ts
                    LEFT JOIN ngram_data nd ON nd.session_date <= ts.date_val
                        AND nd.recency_rank <= 20  -- Only consider most recent 20 samples
                    GROUP BY ts.date_val, nd.ngram_text, nd.ngram_size
                    HAVING COUNT(nd.ngram_time_ms) > 0  -- Only include dates with data
                )
                SELECT 
                    measurement_date,
                    ngram_text,
                    ngram_size,
                    decaying_average_ms,
                    sample_count
                FROM historical_points
                WHERE ngram_text IS NOT NULL
                ORDER BY ngram_text, ngram_size, measurement_date
            """

            params = (time_window_days, user_id, keyboard_id, time_window_days)
            results = self.db.fetchall(query, params)

            # Group results by n-gram text
            trends: Dict[str, List[NGramHistoricalData]] = {}

            for row in results:
                ngram_text = row["ngram_text"]

                historical_data = NGramHistoricalData(
                    ngram_text=ngram_text,
                    ngram_size=row["ngram_size"],
                    measurement_date=datetime.fromisoformat(row["measurement_date"]),
                    decaying_average_ms=float(row["decaying_average_ms"]),
                    sample_count=row["sample_count"],
                )

                if ngram_text not in trends:
                    trends[ngram_text] = []

                trends[ngram_text].append(historical_data)

            # Sort each n-gram's historical data by date
            for ngram_text in trends:
                trends[ngram_text].sort(key=lambda x: x.measurement_date)

            logger.info(
                f"Retrieved performance trends for {len(trends)} n-grams over {time_window_days} days"
            )
            return trends

        except Exception as e:
            logger.error(f"Failed to get performance trends: {e}")
            return {}

    def slowest_n(
        self,
        n: int,
        keyboard_id: str,
        user_id: str,
        ngram_sizes: Optional[List[int]] = None,
        lookback_distance: int = 1000,
        included_keys: Optional[List[str]] = None,
    ) -> List[NGramStats]:
        """
        Find the n slowest n-grams by average speed.

        This method was moved from NGramManager to NGramAnalyticsService
        for better organization of analytics functionality.

        Args:
            n: Number of n-grams to return
            keyboard_id: The ID of the keyboard to filter by
            user_id: The ID of the user to filter by
            ngram_sizes: List of n-gram sizes to include (default is 2-20)
            lookback_distance: Number of most recent sessions to consider
            included_keys: List of characters to filter n-grams by (only n-grams
                         containing exclusively these characters will be returned)

        Returns:
            List of NGramStats objects sorted by speed (slowest first)
        """
        if n <= 0:
            return []

        if ngram_sizes is None:
            ngram_sizes = list(range(2, 21))  # Default to 2-20

        if not ngram_sizes:
            return []

        # Build the query to get the slowest n-grams
        placeholders = ",".join(["?"] * len(ngram_sizes))

        # Build key filtering condition if included_keys is provided
        key_filter_condition = ""
        key_filter_params = []
        if included_keys:
            # Use a simpler approach: filter n-grams by checking if they contain only allowed characters
            # We'll do this filtering after the SQL query in Python code
            key_filter_condition = ""  # Will filter in Python instead
            key_filter_params = []

        query = f"""
            WITH recent_sessions AS (
                SELECT session_id, start_time
                FROM practice_sessions
                WHERE keyboard_id = ? AND user_id = ?
                ORDER BY start_time DESC
                LIMIT ?
            ),
            recent_ngrams AS (
                SELECT
                    ngram_text as ngram,
                    ngram_size,
                    AVG(ms_per_keystroke) as avg_time_ms,
                    COUNT(*) as occurrences,
                    MAX(rs.start_time) as last_used,
                    AVG(ms_per_keystroke) * LOG(COUNT(*)) AS ngram_score
                FROM session_ngram_speed ngram
                inner JOIN recent_sessions rs ON ngram.session_id = rs.session_id
                WHERE ngram_size IN ({placeholders})
                {key_filter_condition}
                GROUP BY ngram_text, ngram_size
                HAVING COUNT(*) >= 3  -- Require at least 3 occurrences
                order by avg_time_ms desc

            )
            select * from recent_ngrams
            order by avg_time_ms desc
            limit ?
        """

        params = (
            [keyboard_id, user_id, lookback_distance] + list(ngram_sizes) + key_filter_params + [n]
        )

        results = self.db.fetchall(query, tuple(params)) if self.db else []
        return_val = [
            NGramStats(
                ngram=row["ngram"],
                ngram_size=row["ngram_size"],
                avg_speed=row["avg_time_ms"] if row["avg_time_ms"] > 0 else 0,
                total_occurrences=row["occurrences"],
                last_used=datetime.fromisoformat(row["last_used"]) if row["last_used"] else None,
                ngram_score=row["avg_time_ms"] * log(row["occurrences"]),
            )
            for row in results
        ]

        # Apply Python-based filtering for included_keys if specified
        if included_keys:
            allowed_chars = set(included_keys)
            return_val = [
                stats for stats in return_val if all(char in allowed_chars for char in stats.ngram)
            ]

        return return_val

    def error_n(
        self,
        n: int,
        keyboard_id: str,
        user_id: str,
        ngram_sizes: Optional[List[int]] = None,
        lookback_distance: int = 1000,
        included_keys: Optional[List[str]] = None,
    ) -> List[NGramStats]:
        """
        Find the n most error-prone n-grams by error count.

        This method was moved from NGramManager to NGramAnalyticsService
        for better organization of analytics functionality.

        Args:
            n: Number of n-grams to return
            keyboard_id: The ID of the keyboard to filter by
            user_id: The ID of the user to filter by
            ngram_sizes: List of n-gram sizes to include (default is 2-20)
            lookback_distance: Number of most recent sessions to consider
            included_keys: List of characters to filter n-grams by (only n-grams
                         containing exclusively these characters will be returned)

        Returns:
            List of NGramStats objects sorted by error count (highest first)
        """
        if n <= 0:
            return []

        if ngram_sizes is None:
            ngram_sizes = list(range(2, 21))  # Default to 2-20

        if not ngram_sizes:
            return []

        # Build the query to get the most error-prone n-grams
        placeholders = ",".join(["?"] * len(ngram_sizes))

        # Build key filtering condition if included_keys is provided
        key_filter_condition = ""
        key_filter_params = []
        if included_keys:
            # Use Python filtering instead of SQL GLOB (will filter after query)
            key_filter_condition = ""  # Will filter in Python instead
            key_filter_params = []

        query = f"""
            WITH recent_sessions AS (
                SELECT session_id
                FROM practice_sessions
                WHERE keyboard_id = ? AND user_id = ?
                ORDER BY start_time DESC
                LIMIT ?
            )
            SELECT
                e.ngram_error_id as ngram_id,
                ngram_text as ngram,
                ngram_size,
                COUNT(*) as error_count,
                MAX(ps.start_time) as last_used
            FROM session_ngram_errors e
            JOIN recent_sessions rs ON e.session_id = rs.session_id
            JOIN practice_sessions ps ON e.session_id = ps.session_id
            WHERE e.ngram_size IN ({placeholders})
            {key_filter_condition}
            GROUP BY ngram_text, ngram_size
            ORDER BY error_count DESC, e.ngram_size
            LIMIT ?
        """

        params = (
            [keyboard_id, user_id, lookback_distance] + list(ngram_sizes) + key_filter_params + [n]
        )

        results = self.db.fetchall(query, tuple(params)) if self.db else []

        return_val = [
            NGramStats(
                ngram=row["ngram"],
                ngram_size=row["ngram_size"],
                avg_speed=0,  # Not applicable for error count
                total_occurrences=row["error_count"],
                last_used=datetime.fromisoformat(row["last_used"]) if row["last_used"] else None,
                ngram_score=0,
            )
            for row in results
        ]

        # Apply Python-based filtering for included_keys if specified
        if included_keys:
            allowed_chars = set(included_keys)
            return_val = [
                stats for stats in return_val if all(char in allowed_chars for char in stats.ngram)
            ]

        return return_val

    def summarize_session_ngrams(self) -> int:
        """
        Summarize session ngram performance for all sessions not yet in session_ngram_summary.
        
        Uses complex CTEs to aggregate data from session_ngram_speed, session_ngram_errors,
        and session_keystrokes tables, then inserts the results into session_ngram_summary.
        
        Returns:
            Number of records inserted into session_ngram_summary
            
        Raises:
            DatabaseError: If the database operation fails
        """
        logger.info("Starting SummarizeSessionNgrams process")
        
        # Complex CTE-based query to summarize session ngram data
        query = """
        WITH MissingSessions AS (
            -- Find sessions not yet summarized
            SELECT DISTINCT 
                ps.session_id,
                ps.user_id,
                ps.start_time as updated_dt,
                k.target_ms_per_keystroke as target_speed_ms,
                k.keyboard_id
            FROM practice_sessions ps
            JOIN keyboards k ON ps.keyboard_id = k.keyboard_id
            WHERE ps.session_id NOT IN (
                SELECT DISTINCT session_id 
                FROM session_ngram_summary
            )
        ),
        SessionSpeedSummary AS (
            -- Aggregate speed data for ngrams
            SELECT 
                ms.session_id,
                ms.user_id,
                ms.keyboard_id,
                ms.target_speed_ms,
                ms.updated_dt,
                sns.ngram_text,
                sns.ngram_size,
                AVG(sns.ms_per_keystroke) as avg_ms_per_keystroke,
                COUNT(*) as speed_instance_count
            FROM MissingSessions ms
            INNER JOIN session_ngram_speed sns ON ms.session_id = sns.session_id
            GROUP BY ms.session_id, ms.user_id, ms.keyboard_id, ms.target_speed_ms, ms.updated_dt, sns.ngram_text, sns.ngram_size
        ),
        AddErrors AS (
            -- Add error counts to speed summary
            SELECT 
                sss.session_id,
                sss.user_id,
                sss.keyboard_id,
                sss.target_speed_ms,
                sss.updated_dt,
                sss.ngram_text,
                sss.ngram_size,
                sss.avg_ms_per_keystroke,
                sss.speed_instance_count,
                COALESCE(COUNT(sne.ngram_error_id), 0) as error_count,
                (sss.speed_instance_count + COALESCE(COUNT(sne.ngram_error_id), 0)) as total_instance_count
            FROM SessionSpeedSummary sss
            LEFT OUTER JOIN session_ngram_errors sne ON (
                sss.session_id = sne.session_id 
                AND sss.ngram_text = sne.ngram_text 
                AND sss.ngram_size = sne.ngram_size
            )
            GROUP BY sss.session_id, sss.user_id, sss.keyboard_id, sss.target_speed_ms, sss.updated_dt, 
                     sss.ngram_text, sss.ngram_size, sss.avg_ms_per_keystroke, sss.speed_instance_count
        ),
        AddKeys AS (
            -- Add individual keystroke data as 1-grams
            SELECT 
                ms.session_id,
                ms.user_id,
                ms.keyboard_id,
                ms.target_speed_ms,
                ms.updated_dt,
                sk.expected_char as ngram_text,
                1 as ngram_size,
                AVG(CAST(sk.time_since_previous AS REAL)) as avg_ms_per_keystroke,
                COUNT(*) as instance_count,
                SUM(sk.is_error) as error_count
            FROM MissingSessions ms
            INNER JOIN session_keystrokes sk ON ms.session_id = sk.session_id
            WHERE sk.time_since_previous IS NOT NULL
            GROUP BY ms.session_id, ms.user_id, ms.keyboard_id, ms.target_speed_ms, ms.updated_dt, sk.expected_char
        ),
        AllNgrams AS (
            -- Union speed/error data with keystroke data
            SELECT 
                session_id, user_id, keyboard_id, target_speed_ms, updated_dt,
                ngram_text, ngram_size, avg_ms_per_keystroke, 
                total_instance_count as instance_count, error_count
            FROM AddErrors
            
            UNION ALL
            
            SELECT 
                session_id, user_id, keyboard_id, target_speed_ms, updated_dt,
                ngram_text, ngram_size, avg_ms_per_keystroke, 
                instance_count, error_count
            FROM AddKeys
        ),
        ReadyToInsert AS (
            -- Final preparation for insertion
            SELECT 
                session_id,
                ngram_text,
                user_id,
                keyboard_id,
                ngram_size,
                avg_ms_per_keystroke,
                target_speed_ms,
                instance_count,
                error_count,
                updated_dt
            FROM AllNgrams
            WHERE avg_ms_per_keystroke > 0 AND instance_count > 0
        )
        INSERT INTO session_ngram_summary (
            session_id, ngram_text, user_id, keyboard_id, ngram_size,
            avg_ms_per_keystroke, target_speed_ms, instance_count, error_count, updated_dt
        )
        SELECT 
            session_id, ngram_text, user_id, keyboard_id, ngram_size,
            avg_ms_per_keystroke, target_speed_ms, instance_count, error_count, updated_dt
        FROM ReadyToInsert;
        """
        
        try:
            logger.info("Executing session ngram summary query")
            cursor = self.db.execute(query)
            rows_affected = cursor.rowcount if cursor.rowcount is not None else 0
            
            logger.info(f"Successfully inserted {rows_affected} records into session_ngram_summary")
            
            # Log summary statistics
            summary_stats = self.db.fetchone(
                "SELECT COUNT(*) as total_records, COUNT(DISTINCT session_id) as unique_sessions FROM session_ngram_summary"
            )
            
            if summary_stats:
                logger.info(f"Total records in session_ngram_summary: {summary_stats['total_records']}")
                logger.info(f"Unique sessions in session_ngram_summary: {summary_stats['unique_sessions']}")
            
            return rows_affected
            
        except Exception as e:
            logger.error(f"Error in SummarizeSessionNgrams: {str(e)}")
            raise

    def add_speed_summary_for_session(self, session_id: str) -> dict:
        """
        Update performance summary for a specific session using decaying average calculation.
        
        Uses the last 20 sessions (including the given session) to calculate decaying averages
        and updates both ngram_speed_summary_curr (merge) and ngram_speed_summary_hist (insert).
        
        Args:
            session_id: The session ID to process
            
        Returns:
            Dictionary with counts of updated and inserted records
            
        Raises:
            DatabaseError: If the database operation fails
        """
        logger.info(f"Starting AddSpeedSummaryForSession for session: {session_id}")
        
        # Get session info for logging
        session_info = self.db.fetchone(
            "SELECT start_time, user_id, keyboard_id FROM practice_sessions WHERE session_id = ?",
            (session_id,)
        )
        
        if not session_info:
            logger.error(f"Session {session_id} not found")
            raise ValueError(f"Session {session_id} not found")
            
        logger.info(f"Processing session {session_id} from {session_info['start_time']}")
        
        # Insert into history table first
        hist_query = """
        WITH SessionContext AS (
            -- Get the target session details
            SELECT 
                ps.session_id,
                ps.user_id,
                ps.keyboard_id,
                ps.start_time,
                k.target_ms_per_keystroke as target_speed_ms
            FROM practice_sessions ps
            JOIN keyboards k ON ps.keyboard_id = k.keyboard_id
            WHERE ps.session_id = ?
        ),
        Recent20Sessions AS (
            -- Get the 20 most recent sessions up to and including the target session
            SELECT 
                ps.session_id,
                ps.start_time,
                ROW_NUMBER() OVER (ORDER BY ps.start_time DESC) as session_rank
            FROM practice_sessions ps
            JOIN SessionContext sc ON ps.user_id = sc.user_id AND ps.keyboard_id = sc.keyboard_id
            WHERE ps.start_time <= sc.start_time
            ORDER BY ps.start_time DESC
            LIMIT 20
        ),
        NgramPerformanceData AS (
            -- Get ngram performance data for recent sessions
            SELECT 
                sns.ngram_text,
                sns.ngram_size,
                sns.avg_ms_per_keystroke,
                sns.instance_count,
                sns.error_count,
                ps.start_time,
                sc.user_id,
                sc.keyboard_id,
                sc.target_speed_ms,
                sc.session_id as target_session_id,
                -- Calculate days ago from target session
                CAST((
                    CASE 
                        WHEN sc.start_time >= ps.start_time 
                        THEN (julianday(sc.start_time) - julianday(ps.start_time))
                        ELSE 0
                    END
                ) AS REAL) as days_ago
            FROM Recent20Sessions r20
            JOIN practice_sessions ps ON r20.session_id = ps.session_id
            JOIN session_ngram_summary sns ON ps.session_id = sns.session_id
            JOIN SessionContext sc ON 1=1
        ),
        DecayingAverages AS (
            -- Calculate decaying averages using exponential weighting
            SELECT 
                user_id,
                keyboard_id,
                target_session_id,
                ngram_text,
                ngram_size,
                target_speed_ms,
                -- Decaying average calculation: weight = 0.9 ^ days_ago
                SUM(avg_ms_per_keystroke * instance_count * POWER(0.9, days_ago)) / 
                    SUM(instance_count * POWER(0.9, days_ago)) as decaying_average_ms,
                SUM(instance_count) as total_sample_count,
                MAX(start_time) as last_measured
            FROM NgramPerformanceData
            GROUP BY user_id, keyboard_id, target_session_id, ngram_text, ngram_size, target_speed_ms
        )
        INSERT INTO ngram_speed_summary_hist (
            summary_id, user_id, keyboard_id, ngram_text, ngram_size,
            decaying_average_ms, target_speed_ms, target_performance_pct,
            meets_target, sample_count, updated_dt
        )
        SELECT 
            lower(hex(randomblob(16))) as summary_id,
            user_id,
            keyboard_id,
            ngram_text,
            ngram_size,
            decaying_average_ms,
            target_speed_ms,
            CASE 
                WHEN target_speed_ms > 0 
                THEN (target_speed_ms / decaying_average_ms) * 100.0
                ELSE 0
            END as target_performance_pct,
            CASE 
                WHEN target_speed_ms > 0 
                THEN decaying_average_ms <= target_speed_ms
                ELSE 0
            END as meets_target,
            total_sample_count as sample_count,
            last_measured as updated_dt
        FROM DecayingAverages;
        """
        
        # Merge query for current summary table
        merge_query = """
        WITH SessionContext AS (
            SELECT 
                ps.session_id,
                ps.user_id,
                ps.keyboard_id,
                ps.start_time,
                k.target_ms_per_keystroke as target_speed_ms
            FROM practice_sessions ps
            JOIN keyboards k ON ps.keyboard_id = k.keyboard_id
            WHERE ps.session_id = ?
        ),
        Recent20Sessions AS (
            SELECT 
                ps.session_id,
                ps.start_time,
                ROW_NUMBER() OVER (ORDER BY ps.start_time DESC) as session_rank
            FROM practice_sessions ps
            JOIN SessionContext sc ON ps.user_id = sc.user_id AND ps.keyboard_id = sc.keyboard_id
            WHERE ps.start_time <= sc.start_time
            ORDER BY ps.start_time DESC
            LIMIT 20
        ),
        NgramPerformanceData AS (
            SELECT 
                sns.ngram_text,
                sns.ngram_size,
                sns.avg_ms_per_keystroke,
                sns.instance_count,
                sns.error_count,
                ps.start_time,
                sc.user_id,
                sc.keyboard_id,
                sc.target_speed_ms,
                sc.session_id as target_session_id,
                CAST((
                    CASE 
                        WHEN sc.start_time >= ps.start_time 
                        THEN (julianday(sc.start_time) - julianday(ps.start_time))
                        ELSE 0
                    END
                ) AS REAL) as days_ago
            FROM Recent20Sessions r20
            JOIN practice_sessions ps ON r20.session_id = ps.session_id
            JOIN session_ngram_summary sns ON ps.session_id = sns.session_id
            JOIN SessionContext sc ON 1=1
        ),
        DecayingAverages AS (
            SELECT 
                user_id,
                keyboard_id,
                target_session_id,
                ngram_text,
                ngram_size,
                target_speed_ms,
                SUM(avg_ms_per_keystroke * instance_count * POWER(0.9, days_ago)) / 
                    SUM(instance_count * POWER(0.9, days_ago)) as decaying_average_ms,
                SUM(instance_count) as total_sample_count,
                MAX(start_time) as last_measured
            FROM NgramPerformanceData
            GROUP BY user_id, keyboard_id, target_session_id, ngram_text, ngram_size, target_speed_ms
        )
        INSERT OR REPLACE INTO ngram_speed_summary_curr (
            summary_id, user_id, keyboard_id, session_id, ngram_text, ngram_size,
            decaying_average_ms, target_speed_ms, target_performance_pct,
            meets_target, sample_count, updated_dt
        )
        SELECT 
            COALESCE(
                (SELECT summary_id FROM ngram_speed_summary_curr 
                 WHERE user_id = da.user_id AND keyboard_id = da.keyboard_id 
                   AND ngram_text = da.ngram_text AND ngram_size = da.ngram_size),
                lower(hex(randomblob(16)))
            ) as summary_id,
            user_id,
            keyboard_id,
            target_session_id as session_id,
            ngram_text,
            ngram_size,
            decaying_average_ms,
            target_speed_ms,
            CASE 
                WHEN target_speed_ms > 0 
                THEN (target_speed_ms / decaying_average_ms) * 100.0
                ELSE 0
            END as target_performance_pct,
            CASE 
                WHEN target_speed_ms > 0 
                THEN decaying_average_ms <= target_speed_ms
                ELSE 0
            END as meets_target,
            total_sample_count as sample_count,
            last_measured as updated_dt
        FROM DecayingAverages da;
        """
        
        try:
            # Execute history insert
            logger.info("Inserting into ngram_speed_summary_hist")
            hist_cursor = self.db.execute(hist_query, (session_id,))
            hist_inserted = hist_cursor.rowcount if hist_cursor.rowcount is not None else 0
            
            # Execute current table merge
            logger.info("Updating ngram_speed_summary_curr")
            curr_cursor = self.db.execute(merge_query, (session_id,))
            curr_updated = curr_cursor.rowcount if curr_cursor.rowcount is not None else 0
            
            result = {
                'hist_inserted': hist_inserted,
                'curr_updated': curr_updated
            }
            
            logger.info(f"Session {session_id}: {hist_inserted} records inserted into hist, {curr_updated} records updated in curr")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in AddSpeedSummaryForSession for session {session_id}: {str(e)}")
            raise

    def catchup_speed_summary(self) -> dict:
        """
        Process all sessions from oldest to newest to catch up speed summaries.
        
        Queries all sessions in chronological order and calls AddSpeedSummaryForSession
        for each one, logging progress and record counts.
        
        Returns:
            Dictionary with total counts and processing summary
            
        Raises:
            DatabaseError: If the database operation fails
        """
        logger.info("Starting CatchupSpeedSummary process")
        
        # Get all sessions ordered from oldest to newest
        sessions = self.db.fetchall(
            """
            SELECT 
                ps.session_id,
                ps.start_time,
                ps.ms_per_keystroke as session_avg_speed
            FROM practice_sessions ps
            ORDER BY ps.start_time ASC
            """
        )
        
        if not sessions:
            logger.info("No sessions found to process")
            return {'total_sessions': 0, 'total_hist_inserted': 0, 'total_curr_updated': 0}
        
        logger.info(f"Found {len(sessions)} sessions to process")
        
        total_hist_inserted = 0
        total_curr_updated = 0
        processed_sessions = 0
        
        for session in sessions:
            session_id = session['session_id']
            start_time = session['start_time']
            avg_speed = session['session_avg_speed']
            
            # Debug message with session info
            print(f"Processing session {session_id}, avg speed: {avg_speed:.2f}ms, datetime: {start_time}")
            logger.info(f"Processing session {session_id}, avg speed: {avg_speed:.2f}ms, datetime: {start_time}")
            
            try:
                # Call AddSpeedSummaryForSession
                result = self.add_speed_summary_for_session(session_id)
                
                hist_inserted = result['hist_inserted']
                curr_updated = result['curr_updated']
                
                # Indented debug message with record counts
                print(f"    Records: {curr_updated} updated in curr, {hist_inserted} inserted in hist")
                logger.info(f"    Records: {curr_updated} updated in curr, {hist_inserted} inserted in hist")
                
                total_hist_inserted += hist_inserted
                total_curr_updated += curr_updated
                processed_sessions += 1
                
            except Exception as e:
                logger.error(f"Error processing session {session_id}: {str(e)}")
                print(f"    ERROR: Failed to process session {session_id}: {str(e)}")
                # Continue with next session rather than failing completely
                continue
        
        summary = {
            'total_sessions': len(sessions),
            'processed_sessions': processed_sessions,
            'total_hist_inserted': total_hist_inserted,
            'total_curr_updated': total_curr_updated
        }
        
        logger.info(f"CatchupSpeedSummary completed: {processed_sessions}/{len(sessions)} sessions processed, "
                   f"{total_curr_updated} total curr updates, {total_hist_inserted} total hist inserts")
        
        print(f"\nCatchup completed: {processed_sessions}/{len(sessions)} sessions processed")
        print(f"Total records updated in curr: {total_curr_updated}")
        print(f"Total records inserted in hist: {total_hist_inserted}")
        
        return summary
