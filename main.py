from flask import Flask, render_template, jsonify, request
from geometry_msgs.msg import Twist
import os
import subprocess
import webbrowser
import threading
import rospy
import signal
import random

app = Flask(__name__)

# ROS initialization
rospy.init_node('turtlebot3_control', anonymous=True, log_level=rospy.WARN)
cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)

class State:
    INIT = 0
    GAZEBO_RUNNING = 1
    SLAM_RUNNING = 2
    WAITING = 3

class Turtlebot3App:
    def __init__(self):
        self.gazebo = None
        self.slam = None
        self.map_name = None
        self.gazebo_launch = False
        self.current_state = State.INIT
        self.random_num()
    
    def random_num(self):
        random_numbers = [random.randint(0, 9) for _ in range(3)]
        self.numbers = ''.join(map(str, random_numbers))

    def check_gazebo(self):
        # Check and launch Gazebo if not already running.
        if self.current_state == State.INIT and not self.gazebo_launch:
            try:
                self.gazebo = subprocess.Popen(['gnome-terminal', '--', 'roslaunch', 'turtlebot3_gazebo', 'turtlebot3_world.launch'])
                if self.gazebo.poll() is None:
                    self.gazebo_launch = True
                    rospy.logwarn('[DONE]: Gazebo opened successfully.')
                    self.current_state = State.GAZEBO_RUNNING
                else:
                    rospy.logerr('[Error]: Failed to launch Gazebo.')
            except Exception as e:
                rospy.logerr(f"[Error]: Failed to launch Gazebo: {e}")
        else:
            rospy.loginfo('[Running] Gazebo is already running.')
        rospy.loginfo(f'[Debug]: Current state at {self.current_state}.')
            
    def navi_map_feature(self):
        # Open map navigation feature.
        if self.current_state == State.GAZEBO_RUNNING:
            try:
                self.navigate = subprocess.Popen(["gnome-terminal", "--", "roslaunch", "turtlebot3_navigation", "turtlebot3_navigation.launch"])
                self.current_state = State.SLAM_RUNNING
            except Exception as e:
                rospy.logerr(f"[Error]: Failed to launch navigation: {e}")
        else:
            rospy.logerr(f'[Error]: You should close SLAM and run Gazebo.')
        rospy.loginfo(f'[Debug]: Current state at {self.current_state}.')
    
    def create_map_feature(self):
        # Create map using SLAM.
        if self.current_state == State.GAZEBO_RUNNING:
            try:
                self.slam = subprocess.Popen(['gnome-terminal', '--', 'roslaunch', 'turtlebot3_slam', 'turtlebot3_slam.launch'])
                if self.slam.poll() is None:
                    rospy.logwarn('[DONE]: SLAM opened successfully.')
                    self.current_state = State.SLAM_RUNNING
                else:
                    rospy.logerr('[Error]: Failed to launch SLAM.')
            except Exception as e:
                rospy.logerr(f"[Error]: Failed to launch SLAM: {e}")
        else:
            rospy.logerr('[Error]: Please open "Gazebo" before using this feature.')
        rospy.loginfo(f'[Debug]: Current state at {self.current_state}.')
    
    def save_map_feature(self):
        # Save the current map.
        if self.current_state == State.SLAM_RUNNING:
            try:
                result = subprocess.run(
                    ['gnome-terminal', '--', 'rosrun', 'map_server', 'map_saver', '-f', f'/home/wpms/map({self.numbers})'],
                    check=True
                )
                rospy.logwarn(f'[DONE]: Map has saved successfully.')
                
                if result.returncode == 0:
                    self.current_state = State.WAITING
                
            except subprocess.CalledProcessError as e:
                rospy.logerr(f"[Error]: Failed to save the map: {e}")
        else:
            rospy.logerr('[Error]: Failed to save the map or SLAM is not running.')
        
        rospy.loginfo(f'[Debug]: Current state at {self.current_state}.')
        
    def exit_feature(self):
        # Terminate all processes and reset state.
        if self.current_state == State.WAITING:
            rospy.loginfo('[DEBUG]: Save complete please close all process.')
            try:
                subprocess.Popen(['killall', 'gnome-terminal-server'])
                subprocess.Popen(['killall', '-9', 'rviz'])
                if self.gazebo_launch:
                    subprocess.Popen(['killall', 'gzserver'])
                    subprocess.Popen(['killall', 'gzclient'])
                rospy.logwarn('[DONE]: Closed all processes successfully.')
                self.reset()
            except Exception as e:
                rospy.logerr(f"[Error]: Terminating processes: {e}")
                return str(e)
            self.current_state = State.GAZEBO_RUNNING
        else:
            try:
                subprocess.Popen(['killall', 'gnome-terminal-server'])
                subprocess.Popen(['killall', '-9', 'rviz'])
                if self.gazebo_launch:
                    subprocess.Popen(['killall', 'gzserver'])
                    subprocess.Popen(['killall', 'gzclient'])
                rospy.logwarn('[DONE]: Closed all processes successfully.')
                self.reset()
            except Exception as e:
                rospy.logerr(f"[Error]: Terminating processes: {e}")
                return str(e)
            self.current_state = State.INIT
    
    def reset(self):
        # Reset internal state and variables.
        self.gazebo = self.slam = None
        self.gazebo_launch = False

turtlebot3_app = Turtlebot3App()

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/check_gazebo')
def check_gazebo_route():
    turtlebot3_app.check_gazebo()
    return jsonify({"result": "Gazebo launching command sent."})

@app.route('/navi_feature')
def navi_feature_route():
    turtlebot3_app.navi_map_feature()
    return jsonify({"result": "Navigate map feature."})

@app.route('/map_feature')
def map_feature_route():
    turtlebot3_app.create_map_feature()
    return jsonify({"result": "Creating map feature."})

@app.route('/save_feature')
def save_feature_route():
    turtlebot3_app.save_map_feature()
    return jsonify({"result": "Saving map feature."})

@app.route('/exit_feature')
def exit_feature_route():
    result = turtlebot3_app.exit_feature()
    return jsonify({"result": result})

@app.route('/joy_command', methods=['POST'])
def joy_command():
    data = request.json
    twist_cmd = Twist()
    twist_cmd.linear.x = float(data['linear_x'])
    twist_cmd.angular.z = float(data['angular_z'])
    cmd_vel_pub.publish(twist_cmd)
    return jsonify({'status': 'success'})

def open_browser():
    if 'WERKZEUG_RUN_MAIN' not in os.environ:
        webbrowser.open_new('http://127.0.0.1:5000/')

def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

def signal_handler(sig, frame):
    rospy.signal_shutdown('Ctrl+C pressed')
    shutdown_server()

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    threading.Timer(1, open_browser).start()
    app.run(debug=True)
