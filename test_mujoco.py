import mujoco
import os

model_path = "src/mujoco_menagerie/franka_emika_panda/kitchen_scene.xml"

if not os.path.exists(model_path):
    print(f"Error: Could not find model at {model_path}")
    exit(1)

# Load the model
try:
    model = mujoco.MjModel.from_xml_path(model_path)
    data = mujoco.MjData(model)
    print("Franka Emika Panda model loaded successfully!")
    
    # Step the simulation 100 times to verify physics engine
    for _ in range(100):
        mujoco.mj_step(model, data)
        
    print(f"Simulation stepped successfully. Final time: {data.time:.3f}s")
except Exception as e:
    print(f"Error loading or simulating model: {e}")
    exit(1)
