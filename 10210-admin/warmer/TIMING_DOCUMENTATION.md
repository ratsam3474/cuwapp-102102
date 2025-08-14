# WhatsApp Warmer Time Tracking Documentation

## How Time is Tracked

### Database Fields
- `started_at` - Timestamp when current warming session started
- `stopped_at` - Timestamp when last warming session stopped  
- `total_duration_minutes` - Cumulative total of all warming time (persisted)

### Time Tracking Flow

#### 1. Starting Warmer
```python
# warmer_engine.py - start_warming()
warmer.started_at = datetime.utcnow()
warmer.stopped_at = None  # Clear for new session
warmer.status = WARMING
# DO NOT recalculate or add previous duration - it's already in total_duration_minutes
```

#### 2. While Running
- Every 60 seconds, check if limit exceeded:
```python
current_session = (now - started_at) / 60
total_so_far = total_duration_minutes + current_session
if total_so_far >= (plan_hours * 60):
    # Auto-stop
```

#### 3. Stopping Warmer
```python
# warmer_engine.py - stop_warming()
if warmer.started_at and not warmer.stopped_at:  # Ensure not already stopped
    warmer.stopped_at = datetime.utcnow()
    session_duration = (stopped_at - started_at) / 60
    warmer.total_duration_minutes += session_duration
    # Save ONCE here only
```

## Common Issues & Solutions

### Issue: Time Jumps/Doubles
**Cause**: Duration calculated in multiple places
**Solution**: Only calculate in `warmer_engine.stop_warming()`

### Issue: 5-Minute Jump on Restart
**Cause**: Re-adding previous session duration on start
**Solution**: Don't recalculate on start - it's already saved

### Issue: Negative or Huge Durations
**Cause**: Clock skew or invalid timestamps
**Solution**: Add sanity checks:
```python
if 0 < duration < 10080:  # Max 1 week
    total += duration
```

## Best Practices

1. **Single Source of Truth**: Only update duration in ONE place (stop_warming)
2. **Atomic Operations**: Use database transactions 
3. **Timestamp Validation**: Always check timestamps are valid before calculating
4. **Idempotency**: Ensure stop can be called multiple times safely
5. **Logging**: Log all duration calculations for debugging

## Testing Checklist

- [ ] Start warmer - check started_at is set
- [ ] Stop warmer - check duration added correctly
- [ ] Restart warmer - ensure no double-counting
- [ ] Auto-stop at limit - verify final duration is accurate
- [ ] Multiple start/stop cycles - cumulative total is correct
- [ ] Edge cases: stop without start, start without stop

## Calculation Examples

### Normal Session
```
Start: 10:00 AM
Stop: 10:30 AM
Duration: 30 minutes
Total: previous_total + 30
```

### Multiple Sessions
```
Session 1: 30 min (total: 30)
Session 2: 45 min (total: 75)
Session 3: 20 min (total: 95)
```

### Auto-Stop at Limit
```
Plan: 2 hours (120 min)
Used: 100 min
Start new: 10:00 AM
Auto-stop: 10:20 AM (at 120 min total)
```