from app import create_app
import argparse
import os

app = create_app()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the CampusManager Flask app')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the app on')
    parser.add_argument('--name', type=str, default='Instance', help='Name of the instance (e.g., Admin, Teacher)')
    args = parser.parse_args()
    
    # Set terminal title
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(f"CampusManager - {args.name} - Port {args.port}")
        except Exception:
            pass
            
    print(f"\n{'='*40}")
    print(f"🚀 CampusManager — Starting Instance: {args.name}")
    print(f"🔌 Port: {args.port}")
    print(f"🔔 Real-time notifications enabled")
    print(f"{'='*40}\n")
    
    # Set unique session cookie name based on port to allow multiple instances
    # This prevents session conflict when running multiple instances on localhost
    app.config['SESSION_COOKIE_NAME'] = f'session_{args.port}'
    app.config['REMEMBER_COOKIE_NAME'] = f'remember_token_{args.port}'
    
    # Use SocketIO to run the app instead of app.run()
    # Allow Werkzeug here for this development/Docker setup.
    app.socketio.run(app, debug=True, port=args.port, host='0.0.0.0', allow_unsafe_werkzeug=True)