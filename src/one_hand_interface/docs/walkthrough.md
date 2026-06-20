# Phase 2: The Classical Skeleton

## What We Achieved
You should now see **two** windows open on your screen: the photorealistic MuJoCo physics simulation, and the ROS 2 RViz interface! 

We successfully connected the visual skeletal mathematical representations of the robot directly to the physics engine.

1. **RViz Integration:** I created a default `view_robot.rviz` configuration file that sets up a 3D grid, the robot's visual meshes, and TF frames.
2. **Launch File Upgrade:** I modified `sim.launch.py` to automatically spawn RViz2 upon launch, feeding it the `robot_state_publisher` data.
3. **Build System Updates:** I modified your `setup.py` so that your RViz configuration is correctly deployed to the `install/` directory every time you build.

## How to Verify
- Look at the RViz window: You should see the robot's 3D mesh perfectly matching the position of the arm in the MuJoCo window.
- In RViz, check the "TF" checkbox on the left panel to see the exact coordinate frames (the red/green/blue arrows) for every single joint and finger.

## Next Steps
All Phase 2 requirements are completed and have been safely committed to the `feature/rich-environment` branch!

Whenever you are ready, we can begin planning **Phase 3**, which involves setting up actual motion planning capabilities (e.g. MoveIt2 or custom inverse kinematics) so that we can command the arm to reach for the donut or the iced tea!
