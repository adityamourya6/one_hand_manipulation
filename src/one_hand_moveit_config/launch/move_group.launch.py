import os
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import yaml
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue
from moveit_configs_utils import MoveItConfigsBuilder

def load_yaml(package_name, file_path):
    package_path = get_package_share_directory(package_name)
    absolute_file_path = os.path.join(package_path, file_path)
    try:
        with open(absolute_file_path, 'r') as file:
            return yaml.safe_load(file)
    except EnvironmentError:
        return None

def generate_launch_description():
    moveit_config = (
        MoveItConfigsBuilder("fer", package_name="one_hand_moveit_config")
        .robot_description(file_path="config/fer.urdf.xacro") # Fake path to avoid error, we override below
        .planning_pipelines(pipelines=["ompl"])
        .joint_limits(file_path="config/joint_limits.yaml")
        .to_moveit_configs()
    )

    # URDF
    pkg_share = FindPackageShare("one_hand_interface")
    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution([pkg_share, "urdf", "panda_mujoco.urdf.xacro"]),
        ]
    )
    robot_description = {"robot_description": ParameterValue(value=robot_description_content, value_type=str)}

    # MoveIt Controllers
    moveit_controllers_yaml = load_yaml('one_hand_moveit_config', 'config/moveit_controllers.yaml')
    moveit_controllers = {
        'moveit_simple_controller_manager': moveit_controllers_yaml['moveit_simple_controller_manager'],
        'moveit_controller_manager': moveit_controllers_yaml['moveit_controller_manager'],
    }
    
    # Trajectory Execution Functionality
    trajectory_execution = {
        'moveit_manage_controllers': True,
        'trajectory_execution.allowed_execution_duration_scaling': 1.2,
        'trajectory_execution.allowed_goal_duration_margin': 0.5,
        'trajectory_execution.allowed_start_tolerance': 0.01,
    }

    parameters_dict = moveit_config.to_dict()
    
    # Load ompl config and manually inject to ensure planning_plugin is set
    ompl_planning_yaml = load_yaml('one_hand_moveit_config', 'config/ompl_planning.yaml')
    if ompl_planning_yaml:
        if 'ompl' not in parameters_dict:
            parameters_dict['ompl'] = {}
        parameters_dict['ompl'].update(ompl_planning_yaml)
        
    parameters_dict.update(robot_description)
    parameters_dict.update(moveit_controllers)
    parameters_dict.update(trajectory_execution)
    parameters_dict['use_sim_time'] = True
    parameters_dict['start_state_max_bounds_error'] = 0.1

    # Start the actual move_group node/action server
    run_move_group_node = Node(
        package='moveit_ros_move_group',
        executable='move_group',
        output='screen',
        parameters=[parameters_dict],
    )

    return LaunchDescription([run_move_group_node])
