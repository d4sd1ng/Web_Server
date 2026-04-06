from flask import Blueprint, request, jsonify

admin_bp = Blueprint('admin', __name__)

users = []  # Simulated in-memory user list

@admin_bp.route('/admin/add-user', methods=['POST'])
def add_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')

    if not username or not password or not role:
        return jsonify({"error": "Username, password, and role are required"}), 400

    users.append({"username": username, "password": password, "role": role})
    return jsonify({"message": f"User {username} added successfully."})

@admin_bp.route('/admin/delete-user', methods=['POST'])
def delete_user():
    data = request.get_json()
    username = data.get('username')

    if not username:
        return jsonify({"error": "Username is required"}), 400

    global users
    users = [user for user in users if user['username'] != username]
    return jsonify({"message": f"User {username} deleted successfully."})

@admin_bp.route('/admin/set-permissions', methods=['POST'])
def set_permissions():
    data = request.get_json()
    username = data.get('username')
    permissions = data.get('permissions')

    if not username or not permissions:
        return jsonify({"error": "Username and permissions are required"}), 400

    user = next((user for user in users if user['username'] == username), None)
    if not user:
        return jsonify({"error": f"User {username} not found"}), 404

    user['permissions'] = permissions
    return jsonify({"message": f"Permissions updated for {username}."})

@admin_bp.route('/admin/logs', methods=['GET'])
def view_logs():
    logs = ["Log 1: System started", "Log 2: Backup created", "Log 3: User added"]  # Placeholder logs
    return jsonify(logs)
