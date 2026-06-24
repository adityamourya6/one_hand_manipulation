import os

xml = """<mujoco>
    <asset>
        <material name="rack_table_wood" rgba="0.6 0.4 0.2 1"/>
        <material name="rack_metal" rgba="0.3 0.3 0.3 1"/>
        <material name="fork_metal" rgba="0.4 0.4 0.4 1"/>
    </asset>
    <worldbody>
        <!-- The Tool Rack Station (Behind the robot) -->
        <!-- Floor is at z = -0.85 -->
        
        <!-- Table Top -->
        <!-- Center at z = 0.375, half-thickness 0.025 -> Surface is exactly at z = 0.40 -->
        <body name="tool_rack_table" pos="-0.7 0 0.375">
            <geom type="box" size="0.2 0.7 0.025" material="rack_table_wood" contype="1" conaffinity="1"/>
            
            <!-- Table Legs (reaching down to z = -0.85) -->
            <!-- Distance from z=0.35 (bottom of table top) to z=-0.85 is 1.2m. Half size = 0.6. Center = -0.25 relative to origin? No, relative to table body (z=0.375) -->
            <!-- Local pos for leg center: -0.625 (so global is 0.375 - 0.625 = -0.25). Bottom is -0.25 - 0.6 = -0.85 -->
            <geom type="box" pos="-0.15 0.65 -0.625" size="0.05 0.05 0.6" material="rack_metal" contype="1" conaffinity="1"/>
            <geom type="box" pos="0.15 0.65 -0.625" size="0.05 0.05 0.6" material="rack_metal" contype="1" conaffinity="1"/>
            <geom type="box" pos="-0.15 -0.65 -0.625" size="0.05 0.05 0.6" material="rack_metal" contype="1" conaffinity="1"/>
            <geom type="box" pos="0.15 -0.65 -0.625" size="0.05 0.05 0.6" material="rack_metal" contype="1" conaffinity="1"/>
        </body>

        <!-- Rack Backbone (elevated above the table to let tools hang) -->
        <body name="tool_rack_backbone" pos="-0.75 0 0.7">
            <!-- The main horizontal bar -->
            <geom type="box" size="0.02 0.65 0.02" material="rack_metal" contype="1" conaffinity="1"/>
            
            <!-- Supports connecting the backbone to the table surface -->
            <!-- Table surface is z=0.4. Backbone is z=0.7. Distance = 0.3. Half-size = 0.15. Center = 0.55 -->
            <geom type="box" pos="0 0.6 -0.15" size="0.02 0.02 0.15" material="rack_metal" contype="1" conaffinity="1"/>
            <geom type="box" pos="0 -0.6 -0.15" size="0.02 0.02 0.15" material="rack_metal" contype="1" conaffinity="1"/>
"""

# We have 6 tools. Spacing = 0.2m
# y positions relative to rack center
y_positions = [-0.5, -0.3, -0.1, 0.1, 0.3, 0.5]
tools = [
    "franka_hand",
    "cobot_pump",
    "robotiq_2f85",
    "allegro_hand",
    "shadow_dex_ee",
    "power_drill"
]

for i, y in enumerate(y_positions):
    tool_name = tools[i]
    xml += f"""
            <!-- Slot {i+1} for {tool_name} -->
            <body name="rack_slot_{tool_name}" pos="0 {y} 0">
                <!-- Left Prong -->
                <!-- Extending towards the robot (+x direction) -->
                <geom type="box" pos="0.06 0.036 0" size="0.06 0.01 0.01" material="fork_metal" contype="1" conaffinity="1"/>
                <!-- Right Prong -->
                <geom type="box" pos="0.06 -0.036 0" size="0.06 0.01 0.01" material="fork_metal" contype="1" conaffinity="1"/>
            </body>
"""

xml += """        </body>
    </worldbody>
</mujoco>
"""

with open("/home/mourya/one_hand_ws/src/one_hand_interface/config/tool_rack.xml", "w") as f:
    f.write(xml)

print("tool_rack.xml generated with dedicated table.")
