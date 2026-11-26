import subprocess

def spawn_sdf(name, sdf_xml, x, y, z):
    sdf_path = f'/tmp/{name}.sdf'
    with open(sdf_path, 'w') as f:
        f.write(sdf_xml)
    subprocess.run([
        'ros2', 'run', 'gazebo_ros', 'spawn_entity.py',
        '-entity', name, '-file', sdf_path,
        '-x', str(x), '-y', str(y), '-z', str(z)
    ])

def make_box_sdf(name, sx, sy, sz, r, g, b, is_static=False, mass=0.12):
    static_tag = "<static>true</static>" if is_static else ""
    return f"""<?xml version='1.0'?>
<sdf version='1.6'>
  <model name='{name}'>
    {static_tag}
    <link name='link'>
      <inertial>
        <mass>{mass}</mass>
        <inertia><ixx>0.0001</ixx><iyy>0.0001</iyy><izz>0.0001</izz></inertia>
      </inertial>
      <velocity_decay>
        <linear>0.02</linear>
        <angular>0.15</angular>
      </velocity_decay>
      <collision name='collision'>
        <geometry><box><size>{sx} {sy} {sz}</size></box></geometry>
        <surface>
          <friction><ode><mu>20.0</mu><mu2>20.0</mu2></ode></friction>
          <contact><ode><kp>20000.0</kp><kd>100.0</kd></ode></contact>
        </surface>
      </collision>
      <visual name='visual'>
        <geometry><box><size>{sx} {sy} {sz}</size></box></geometry>
        <material><ambient>{r} {g} {b} 1</ambient><diffuse>{r} {g} {b} 1</diffuse></material>
      </visual>
    </link>
  </model>
</sdf>"""

if __name__ == '__main__':
    # Kolun rahat uzandigi 0.66m mesafeye alma tezgahi ve kupler
    spawn_sdf('alma_tezgahi', make_box_sdf('alma_tezgahi', 0.26, 0.46, 0.09, 0.25, 0.25, 0.28, is_static=True), 0.66, 0.0, 0.045)
    spawn_sdf('kup_kirmizi', make_box_sdf('kup_kirmizi', 0.05, 0.05, 0.05, 0.9, 0.1, 0.1), 0.66, -0.14, 0.115)
    spawn_sdf('kup_yesil',   make_box_sdf('kup_yesil',   0.05, 0.05, 0.05, 0.1, 0.8, 0.1), 0.67,  0.00, 0.115)
    spawn_sdf('kup_mavi',    make_box_sdf('kup_mavi',    0.05, 0.05, 0.05, 0.1, 0.3, 0.9), 0.66,  0.14, 0.115)
    
    # Sol tarafta ayni 0.66m mesafede hedef platformu
    spawn_sdf('hedef_platform', make_box_sdf('hedef_platform', 0.28, 0.28, 0.09, 0.15, 0.15, 0.15, is_static=True), 0.0, 0.66, 0.045)
