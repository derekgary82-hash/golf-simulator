# 🏌️ Golf Simulator

A comprehensive golf simulator with camera access, swing analysis, and a video game-style driving range experience.

## Features

### 1. **Swing Analysis** (`golf_swing_analyzer.py`)
- Real-time pose detection using MediaPipe
- Club head speed estimation from camera feed
- Launch angle calculation
- Swing phase detection (backswing, downswing, follow-through)
- Advanced 3D ball flight physics simulation
- Wind and spin effects
- Trajectory visualization

**Requirements:**
```bash
pip install opencv-python mediapipe numpy matplotlib
```

**Usage:**
```bash
python golf_swing_analyzer.py
```

### 2. **Driving Range Simulator** (`golf_driving_range.py`)
- Video game-style graphics using Pygame
- Realistic ball physics with gravity and drag
- Wind effects on ball flight
- Target flags at various distances
- Score tracking and statistics
- Power and angle control
- Real-time trajectory preview
- Session statistics saved to JSON

**Requirements:**
```bash
pip install pygame
```

**Usage:**
```bash
python golf_driving_range.py
```

## Controls

### Swing Analyzer
- Record video or use webcam
- Auto-detects swing phases
- Generates swing report with metrics

### Driving Range
- **LEFT/RIGHT Arrow Keys**: Adjust launch angle
- **Hold Mouse Button**: Charge power (0-100%)
- **Release Mouse**: Execute swing
- **SPACE**: Reset ball position
- **W Key**: Change wind conditions

## Output Files

- `output_annotated.mp4` - Annotated swing video
- `trajectory.png` - Ball flight trajectory plot
- `swing_metrics.json` - Detailed swing analysis
- `session_stats.json` - Session statistics

## Features

✅ Camera-based swing detection  
✅ Realistic ball physics (drag, spin, wind)  
✅ 3D trajectory visualization  
✅ Real-time performance metrics  
✅ Historical session tracking  
✅ Game-style UI and animations  

## Future Enhancements

- [ ] AR overlay for real camera feed
- [ ] Club selection (driver, iron, putter)
- [ ] Course simulation
- [ ] Multiplayer leaderboards
- [ ] AI coaching feedback
- [ ] Ball impact zone detection

## Setup

1. Clone this repository
2. Install dependencies for each module
3. For swing analyzer: provide `input_swing.mp4` or use webcam
4. For driving range: just run and practice!

## Performance Notes

- Swing analyzer: ~30-60 FPS on modern hardware
- Driving range: 60 FPS target
- Camera resolution: 1080p recommended for swing analysis
