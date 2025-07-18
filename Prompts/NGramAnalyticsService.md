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
- `last_updated`: Last update timestamp
- `created_at`: Creation timestamp

## Database Schema

### ngram_speed_summaries Table
```sql
CREATE TABLE IF NOT EXISTS ngram_speed_summaries (
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
    last_updated TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (keyboard_id) REFERENCES keyboards(keyboard_id) ON DELETE CASCADE,
    UNIQUE (user_id, keyboard_id, ngram_text, ngram_size)
);
```

### Indexes
- `idx_ngram_summaries_user_keyboard`: On (user_id, keyboard_id)
- `idx_ngram_summaries_performance`: On (target_performance_pct, meets_target)

## Core Methods

### refresh_speed_summaries(user_id, keyboard_id)
Recalculates decaying averages and updates the summary table from raw session data.

**Process:**
1. Get target speed from keyboard settings
2. Query recent sessions (last 100) for user/keyboard
3. Group n-gram measurements by text and size
4. Calculate decaying average for each n-gram
5. Calculate performance percentage vs target
6. Upsert summary records

### get_speed_heatmap_data(user_id, keyboard_id, options)
Returns formatted heatmap data for UI visualization.

**Options:**
- `target_speed_ms`: Override target speed
- `ngram_size_filter`: Filter by specific n-gram size
- `exclude_successful`: Hide n-grams meeting target
- `sort_order`: "worst_to_best" or "best_to_worst"

**Color Coding:**
- **Green (#90EE90)**: Meets target speed
- **Amber (#FFD700)**: 75%+ of target performance
- **Grey (#D3D3D3)**: Below 75% of target

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

## Performance Optimization
- **Summary Table**: Pre-calculated metrics for fast queries
- **Indexes**: Optimized for common query patterns
- **Batch Processing**: Efficient summary refresh
- **Parameterized Queries**: Prevents SQL injection

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
4. Summary table is created automatically on first use

## Dependencies
- `pydantic`: Data validation and type checking
- `DatabaseManager`: Database operations
- `NGramManager`: Core n-gram operations
- `sqlite3`/`psycopg2`: Database connectivity
