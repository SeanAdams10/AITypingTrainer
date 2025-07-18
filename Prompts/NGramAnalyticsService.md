# NGram Analytics Service Specification

## Overview
The `NGramAnalyticsService` provides comprehensive analytics and performance analysis for n-gram typing performance. It implements a decaying average algorithm for recent performance weighting, maintains performance summaries with historical tracking, and provides heatmap data for visualization.

## Key Features
- **Decaying Average Algorithm**: ELO-like system where recent measurements have exponentially higher weights
- **Performance Summaries**: Cached summary table for fast heatmap queries
- **Historical Analysis**: Track performance trends over time
- **Analytics Migration**: Moved `slowest_n` and `error_n` methods from `NGramManager`
- **Heatmap Data**: Formatted data for UI visualization with color coding

## Decaying Average Algorithm
The decaying average algorithm uses exponential weighting to give more importance to recent performance measurements:

```
weight = decay_factor ^ (days_ago)
```

Where:
- `decay_factor` = 0.9 (configurable)
- `days_ago` = number of days since the most recent measurement
- Only the most recent 20 measurements are considered
- More recent measurements receive exponentially higher weights

### Example
For measurements [100ms, 200ms, 300ms] taken [3 days ago, 2 days ago, today]:
- Today's measurement (300ms) gets weight: 0.9^0 = 1.0
- 2 days ago (200ms) gets weight: 0.9^2 = 0.81
- 3 days ago (100ms) gets weight: 0.9^3 = 0.729

Final weighted average = (1.0×300 + 0.81×200 + 0.729×100) / (1.0 + 0.81 + 0.729)

## Data Models

### NGramPerformanceData
Core performance metrics for an n-gram:
- `ngram_text`: The n-gram text (1-50 chars)
- `ngram_size`: Size of the n-gram (1-20)
- `decaying_average_ms`: Weighted average performance in milliseconds
- `target_performance_pct`: Percentage of target performance achieved
- `sample_count`: Number of measurements included
- `last_measured`: Timestamp of most recent measurement
- `performance_category`: "green", "amber", or "grey"

### NGramHeatmapData
Extended data for heatmap visualization:
- All fields from `NGramPerformanceData`
- `decaying_average_wpm`: Performance in words per minute
- `color_code`: Hex color code for visualization

### NGramSummaryData
Database model for cached summaries:
- `summary_id`: UUID primary key
- `user_id`: User identifier
- `keyboard_id`: Keyboard identifier
- `ngram_text`: The n-gram text
- `ngram_size`: Size of the n-gram
- `decaying_average_ms`: Weighted average performance
- `target_speed_ms`: Target speed for this keyboard
- `target_performance_pct`: Performance percentage
- `meets_target`: Boolean indicating if target is met
- `sample_count`: Number of measurements
- `updated_dt`: High-precision datetime of last update

### NGramHistoricalData
Database model for historical performance tracking:
- `history_id`: UUID primary key
- `user_id`: User identifier
- `keyboard_id`: Keyboard identifier
- `ngram_text`: The n-gram text
- `ngram_size`: Size of the n-gram
- `decaying_average_ms`: Weighted average performance at time of measurement
- `target_speed_ms`: Target speed for this keyboard
- `target_performance_pct`: Performance percentage at time of measurement
- `meets_target`: Boolean indicating if target was met
- `sample_count`: Number of measurements used in calculation
- `updated_dt`: High-precision datetime when this measurement was taken

## Database Schema

### ngram_speed_summary_curr Table
```sql
CREATE TABLE IF NOT EXISTS ngram_speed_summary_curr (
    summary_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    keyboard_id TEXT NOT NULL,
    ngram_text TEXT NOT NULL,
    ngram_size INTEGER NOT NULL,
    decaying_average_ms REAL NOT NULL,
    target_speed_ms REAL NOT NULL,
    target_performance_pct REAL NOT NULL,
    meets_target BOOLEAN NOT NULL,
    sample_count INTEGER NOT NULL,
    updated_dt TEXT NOT NULL,  -- TIMESTAMP(6) for PostgreSQL
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (keyboard_id) REFERENCES keyboards(keyboard_id) ON DELETE CASCADE,
    UNIQUE (user_id, keyboard_id, ngram_text, ngram_size)
);
```

### Indexes
- `idx_ngram_summary_curr_user_keyboard`: On (user_id, keyboard_id)
- `idx_ngram_summary_curr_performance`: On (target_performance_pct, meets_target)

### ngram_speed_summary_hist Table
```sql
CREATE TABLE IF NOT EXISTS ngram_speed_summary_hist (
    history_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    keyboard_id TEXT NOT NULL,
    ngram_text TEXT NOT NULL,
    ngram_size INTEGER NOT NULL,
    decaying_average_ms REAL NOT NULL,
    target_speed_ms REAL NOT NULL,
    target_performance_pct REAL NOT NULL,
    meets_target BOOLEAN NOT NULL,
    sample_count INTEGER NOT NULL,
    updated_dt TEXT NOT NULL,  -- TIMESTAMP(6) for PostgreSQL
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (keyboard_id) REFERENCES keyboards(keyboard_id) ON DELETE CASCADE
);
```

### History Table Indexes
- `idx_ngram_summary_hist_user_keyboard`: On (user_id, keyboard_id)
- `idx_ngram_summary_hist_ngram`: On (ngram_text, ngram_size)
- `idx_ngram_summary_hist_date`: On (updated_dt)

## Core Methods

### refresh_speed_summaries(user_id, keyboard_id)
Recalculates decaying averages and updates the summary table from raw session data using a **dual-insert approach** for historical tracking.

**Dual-Insert Process:**
1. Get target speed from keyboard settings
2. Query recent session ngrams (last 20 measurements)
3. Calculate decaying average for each unique ngram
4. **Dual-insert each summary record:**
   - Insert/replace into `ngram_speed_summary_curr` (current data)
   - Insert into `ngram_speed_summary_hist` (historical record)
5. Calculate performance percentages and target achievement
6. Generate timestamps for both current and historical records

### get_heatmap_data(user_id, keyboard_id, size_filter, sort_by, reverse_sort)
Returns formatted heatmap data with color coding and performance metrics.

**Parameters:**
- `size_filter`: Filter by ngram size (optional)
- `sort_by`: Sort criterion (wpm, accuracy, etc.)
- `reverse_sort`: Sort direction

**Returns:** List of NGramHeatmapData with color codes

### get_ngram_history(user_id, keyboard_id, ngram_text=None)
Returns historical performance data for trend analysis and improvement tracking.
### slowest_n(n, keyboard_id, user_id, options)
Returns the n slowest n-grams using decaying averages.

**Moved from NGramManager with improvements:**
- Uses cached summary table for performance
- Implements decaying average weighting
- Maintains same interface for compatibility

### error_n(n, keyboard_id, user_id, options)
Returns the n most error-prone n-grams.

**Moved from NGramManager with improvements:**
- Uses recent session data
- Maintains same interface for compatibility

## Historical Tracking Architecture

### Dual-Insert Strategy
The service implements a **dual-insert approach** for comprehensive historical tracking:

- **Current Summary Table** (`ngram_speed_summary_curr`): Maintains latest performance metrics
- **History Table** (`ngram_speed_summary_hist`): Accumulates all historical measurements
- **Simultaneous Inserts**: Every refresh operation writes to both tables
- **No Data Movement**: History records are never moved or deleted, only accumulated

### Benefits of Dual-Insert
- **Performance**: No expensive data migration operations
- **Simplicity**: Straightforward insert operations only
- **Reliability**: No risk of data loss during moves
- **Query Efficiency**: Optimized tables for different access patterns
- **Historical Integrity**: Complete audit trail of all measurements

### Data Flow
```
Session Data → refresh_speed_summaries() → ┌─ INSERT/REPLACE → ngram_speed_summary_curr
                                          └─ INSERT → ngram_speed_summary_hist
```

## Performance Optimization
- **Summary Table**: Pre-calculated metrics for fast queries
- **History Table**: Separate optimized storage for time-series data
- **Indexes**: Optimized for common query patterns
- **Batch Processing**: Efficient summary refresh
- **Parameterized Queries**: Prevents SQL injection
- **Dual-Insert Efficiency**: Minimal overhead for historical tracking

## Error Handling
- Graceful handling of missing keyboard data
- Validation of input parameters
- Proper exception logging
- Fallback to empty results on errors

## Testing Requirements
- Unit tests for all methods
- Integration tests with temporary database
- Edge case testing (empty data, invalid parameters)
- Performance tests for large datasets
- Decaying average calculation validation

## UI Integration
The service provides data for:
- **Heatmap Grid**: Visual performance overview
- **Filtering**: Size, performance, sort options
- **Color Coding**: Immediate visual feedback
- **WPM Display**: User-friendly speed metrics

## Migration Notes
When migrating from NGramManager:
1. Update imports to use NGramAnalyticsService
2. Call `refresh_speed_summaries()` before analytics queries
3. No interface changes required for `slowest_n()` and `error_n()`
4. Both summary and history tables are created automatically during database initialization
5. Historical data accumulates automatically from first refresh operation
6. Use `get_ngram_history()` for trend analysis and historical performance tracking

## Dependencies
- `pydantic`: Data validation and type checking
- `DatabaseManager`: Database operations
- `NGramManager`: Core n-gram operations
- `sqlite3`/`psycopg2`: Database connectivity
