from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'one_hand_interface'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*.xacro')),
        (os.path.join('share', package_name, 'rviz'), glob('rviz/*.rviz')),
    ] + [(os.path.join('share', package_name, root), [os.path.join(root, f) for f in files]) 
         for root, _, files in os.walk('config')],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='mourya',
    maintainer_email='mourya@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'joint_state_listener = one_hand_interface.joint_state_listener:main',
        ],
    },
)
