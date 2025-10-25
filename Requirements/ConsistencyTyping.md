# Consistency Typing Screen Specification

## 1. Overview

The Consistency Typing screen is an interactive interface focused on developing consistent typing rhythm rather than speed or accuracy alone. The goal is to help users type smoothly with minimal variability between keystrokes, eliminating the "fits and starts" pattern common in typing. This screen is based on the existing typing drill architecture but emphasizes timing consistency metrics and provides rhythm-based feedback.

---

## 2. Functional Requirements

### 2.1 Initialization and Setup

- **Text Input**: Similar to the standard typing drill, either a snippet ID or text is passed in, along with start/end indices
- **Mode Selection**: User chooses between two consistency modes before starting:
  - **Metronome-Led Mode**: User sets desired pace (e.g., 400ms per keystroke)
  - **User-Led Mode**: User types at comfortable speed, system analyzes rhythm

### 2.2 Metronome-Led Mode

#### 2.2.1 Configuration
- **Target Pace Setting**: User sets desired milliseconds per keystroke (range: 200ms - 2000ms, default: 400ms)
- **Metronome Options**: User selects beat frequency:
  - Every keystroke (1:1 ratio)
  - Every 4 keystrokes (4:1 ratio) 
  - Every 8 keystrokes (8:1 ratio)
- **Audio Feedback**: Audible metronome beeps at specified intervals using system audio

#### 2.2.2 Behavior
- Metronome starts when user begins typing (first keystroke)
- Visual metronome indicator shows beat timing
- Target speed is fixed based on user's pace setting
- Variability measured against the set target pace

### 2.3 User-Led Mode

#### 2.3.1 Behavior
- No metronome audio
- System analyzes user's natural typing rhythm from keystroke logs
- Target speed dynamically calculated as rolling average of recent keystrokes
- Adapts to user's comfortable pace in real-time

#### 2.3.2 Dynamic Target Calculation
- Uses rolling window of last 10-20 keystrokes to determine current target pace
- Updates target speed every 5 keystrokes to smooth out variations
- Ignores extreme outliers (>3 standard deviations) when calculating target

### 2.4 Core Metrics and Display

#### 2.4.1 Primary Metrics
- **Target Speed**: Displayed in milliseconds per keystroke
  - Metronome mode: Fixed user-set value
  - User-led mode: Dynamic rolling average
- **Current Speed**: Real-time milliseconds per keystroke for last keystroke
- **Current Variability**: Standard deviation of keystroke intervals in milliseconds
  - Calculated from last 10-20 keystrokes
  - Target variability is always 0ms (perfect consistency)

#### 2.4.2 Variability Visualization
- **Progress Bar/Fuel Gauge**: Visual indicator of typing consistency
  - **Green Zone** (0-50ms variability): Excellent consistency
  - **Yellow Zone** (50-100ms variability): Good consistency  
  - **Orange Zone** (100-200ms variability): Moderate consistency
  - **Red Zone** (>200ms variability): Poor consistency
- **Color Coding**: Background or border color changes based on current variability zone
- **Numerical Display**: Shows exact variability value (e.g., "±45ms")

### 2.5 UI Layout and Components

#### 2.5.1 Top Section - Mode and Settings
- Mode indicator (Metronome-Led / User-Led)
- Target pace setting (editable in Metronome mode, read-only in User-Led)
- Metronome controls (frequency selection, volume) - Metronome mode only

#### 2.5.2 Main Metrics Display
```
Target Speed: 400ms/keystroke    Current Speed: 385ms/keystroke
Current Variability: ±45ms      [████████░░] Excellent Consistency
```

#### 2.5.3 Text Display Area
- Same text highlighting as standard typing drill:
  - Correct characters: **green italic**
  - Incorrect characters: **red bold**
  - Untyped characters: plain black regular
- Handles newlines with ↵ symbol representation

#### 2.5.4 Progress Indicators
- **Characters Progress**: Same as standard drill (completion percentage)
- **Consistency Progress**: Variability gauge with color zones
- **Rhythm Progress**: Visual representation of keystroke timing pattern

#### 2.5.5 Metronome Visual Indicator (Metronome Mode Only)
- Pulsing circle or bar that beats with metronome
- Changes color on beat (e.g., blue → white → blue)
- Shows next expected beat timing

### 2.6 Timing and Calculation Logic

#### 2.6.1 Keystroke Timing Collection
- Record precise timestamp for each keystroke (same as standard drill)
- Calculate intervals between consecutive keystrokes
- Exclude backspace keystrokes from timing calculations
- Handle first keystroke (no previous interval)

#### 2.6.2 Variability Calculation
```python
# Standard deviation of keystroke intervals
intervals = [time_between_keystrokes for last N keystrokes]
variability = standard_deviation(intervals)
```

#### 2.6.3 Target Speed Updates (User-Led Mode)
```python
# Rolling average with outlier filtering
recent_intervals = last_N_keystroke_intervals
filtered_intervals = remove_outliers(recent_intervals, threshold=3_std_dev)
target_speed = mean(filtered_intervals)
```

### 2.7 Audio Implementation

#### 2.7.1 Metronome Audio
- Use system audio capabilities (PySide6 QSound or similar)
- Simple beep sound (sine wave, 800Hz, 100ms duration)
- Volume control (0-100%, default 50%)
- Option to mute metronome while keeping visual indicator

#### 2.7.2 Audio Timing
- Precise timing synchronized with target pace
- Compensate for audio latency where possible
- Graceful degradation if audio unavailable

### 2.8 Session Management and Persistence

#### 2.8.1 Session Data
- All standard typing drill session data
- Additional consistency-specific metrics:
  - Mode used (metronome/user-led)
  - Target pace setting (if metronome mode)
  - Final variability score
  - Consistency zones achieved (time spent in each color zone)
  - Metronome settings used

#### 2.8.2 Keystroke Data Enhancement
- Same keystroke recording as standard drill
- Additional timing analysis for consistency metrics
- Variability calculations stored for historical analysis

### 2.9 Completion and Results

#### 2.9.1 Completion Dialog
- Standard typing statistics (WPM, accuracy, etc.)
- **Consistency-specific results**:
  - Final variability score (±Xms)
  - Consistency rating (Excellent/Good/Moderate/Poor)
  - Time spent in each consistency zone
  - Rhythm improvement suggestions

#### 2.9.2 Consistency Rating Scale
- **Excellent**: <50ms average variability
- **Good**: 50-100ms average variability  
- **Moderate**: 100-200ms average variability
- **Poor**: >200ms average variability

### 2.10 Integration with Existing System

#### 2.10.1 Navigation
- Accessible from main menu as "Consistency Practice"
- Can be launched with same text/snippet as standard typing drill
- Returns to main menu or offers retry option

#### 2.10.2 Database Integration
- Extends existing session and keystroke tables
- New table: `consistency_sessions` for mode-specific data
- Maintains compatibility with existing analytics

#### 2.10.3 User Settings
- Save preferred metronome settings
- Default mode preference (metronome/user-led)
- Audio preferences (volume, frequency)

---

## 3. Technical Implementation Notes

### 3.1 File Structure
- `desktop_ui/consistency_typing.py` - Main UI implementation
- Inherits from or closely follows `TypingDrillScreen` architecture
- Separate metronome audio handling class
- Timing analysis utilities

### 3.2 Dependencies
- PySide6 for UI (consistent with existing codebase)
- Audio libraries for metronome (QSound or platform-specific)
- Same database and model dependencies as typing drill

### 3.3 Performance Considerations
- Efficient real-time variability calculations
- Smooth metronome timing without UI blocking
- Minimal memory usage for keystroke interval storage

### 3.4 Error Handling
- Graceful audio failure handling
- Timing calculation edge cases (single keystroke, etc.)
- Mode switching validation

---

## 4. User Experience Flow

### 4.1 Typical Metronome Session
1. User selects "Consistency Practice" from main menu
2. Chooses text/snippet for practice
3. Selects "Metronome-Led" mode
4. Sets target pace (e.g., 400ms/keystroke)
5. Chooses metronome frequency (every 4 beats)
6. Starts typing - metronome begins
7. Focuses on matching metronome rhythm
8. Monitors variability gauge for consistency feedback
9. Completes session with consistency rating

### 4.2 Typical User-Led Session
1. User selects "Consistency Practice" from main menu
2. Chooses text/snippet for practice  
3. Selects "User-Led" mode
4. Begins typing at comfortable pace
5. System adapts target speed to user's rhythm
6. User focuses on maintaining steady rhythm
7. Monitors variability feedback for improvement
8. Completes session with consistency analysis

---

## 5. Success Metrics

### 5.1 User Improvement Indicators
- Decreasing variability scores over time
- More time spent in green consistency zone
- Improved rhythm stability in longer sessions
- Better consistency across different text types

### 5.2 Feature Effectiveness
- User preference between metronome vs user-led modes
- Correlation between consistency practice and overall typing improvement
- User engagement with consistency features vs standard speed/accuracy drills

---

This specification provides a comprehensive framework for implementing a consistency-focused typing practice tool that complements the existing speed and accuracy-focused typing drill while maintaining architectural consistency with the current codebase.
