#!/usr/bin/env python3
"""
Workspace Management Script
Helps manage multiple trading bot projects and switch between workspaces
"""

import os
import shutil
import json
import datetime
import subprocess
import sys
from pathlib import Path

class WorkspaceManager:
    def __init__(self):
        self.workspaces_file = "workspaces.json"
        self.workspaces = self.load_workspaces()
    
    def load_workspaces(self):
        """Load workspace configurations"""
        if os.path.exists(self.workspaces_file):
            try:
                with open(self.workspaces_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Could not load workspaces: {e}")
                return {}
        return {}
    
    def save_workspaces(self):
        """Save workspace configurations"""
        try:
            with open(self.workspaces_file, 'w') as f:
                json.dump(self.workspaces, f, indent=2)
        except Exception as e:
            print(f"❌ Could not save workspaces: {e}")
    
    def add_workspace(self, name, path, description=""):
        """Add a new workspace"""
        if not os.path.exists(path):
            print(f"❌ Path does not exist: {path}")
            return False
        
        self.workspaces[name] = {
            "path": os.path.abspath(path),
            "description": description,
            "created": datetime.datetime.now().isoformat(),
            "last_used": datetime.datetime.now().isoformat()
        }
        self.save_workspaces()
        print(f"✅ Added workspace: {name} -> {path}")
        return True
    
    def remove_workspace(self, name):
        """Remove a workspace"""
        if name in self.workspaces:
            del self.workspaces[name]
            self.save_workspaces()
            print(f"✅ Removed workspace: {name}")
        else:
            print(f"❌ Workspace not found: {name}")
    
    def list_workspaces(self):
        """List all workspaces"""
        if not self.workspaces:
            print("📁 No workspaces configured")
            return
        
        print("📁 Configured Workspaces:")
        print("=" * 60)
        for name, info in self.workspaces.items():
            current = " (CURRENT)" if os.path.abspath(os.getcwd()) == info["path"] else ""
            print(f"🔹 {name}{current}")
            print(f"   📍 Path: {info['path']}")
            print(f"   📝 Description: {info['description']}")
            print(f"   📅 Created: {info['created'][:10]}")
            print(f"   🕒 Last used: {info['last_used'][:10]}")
            print()
    
    def switch_workspace(self, name):
        """Switch to a different workspace"""
        if name not in self.workspaces:
            print(f"❌ Workspace not found: {name}")
            return False
        
        workspace_path = self.workspaces[name]["path"]
        current_path = os.getcwd()
        
        if os.path.abspath(current_path) == workspace_path:
            print(f"✅ Already in workspace: {name}")
            return True
        
        print(f"🔄 Switching to workspace: {name}")
        print(f"   From: {current_path}")
        print(f"   To: {workspace_path}")
        
        # Update last used timestamp
        self.workspaces[name]["last_used"] = datetime.datetime.now().isoformat()
        self.save_workspaces()
        
        # Change directory
        try:
            os.chdir(workspace_path)
            print(f"✅ Switched to workspace: {name}")
            return True
        except Exception as e:
            print(f"❌ Could not switch to workspace: {e}")
            return False
    
    def create_new_workspace(self, name, base_path=None, template="trading_bot"):
        """Create a new workspace from template"""
        if base_path is None:
            base_path = os.path.dirname(os.getcwd())
        
        workspace_path = os.path.join(base_path, name)
        
        if os.path.exists(workspace_path):
            print(f"❌ Workspace already exists: {workspace_path}")
            return False
        
        print(f"🏗️ Creating new workspace: {name}")
        print(f"📍 Location: {workspace_path}")
        
        try:
            # Create workspace directory
            os.makedirs(workspace_path, exist_ok=True)
            
            # Copy template files if available
            if template == "trading_bot" and os.path.exists("tradingbot_new.py"):
                self.copy_template_files(workspace_path)
            
            # Add to workspace list
            self.add_workspace(name, workspace_path, f"Trading bot workspace: {name}")
            
            print(f"✅ Created workspace: {name}")
            print(f"💡 To switch to this workspace: python workspace_management.py switch {name}")
            
            return True
            
        except Exception as e:
            print(f"❌ Could not create workspace: {e}")
            return False
    
    def copy_template_files(self, target_path):
        """Copy template files to new workspace"""
        template_files = [
            "requirements.txt",
            "README.md",
            "INSTALLATION_GUIDE.md",
            "API_SETUP_GUIDE.md",
            "OPTIONAL_DEPENDENCIES.md",
            "install_dependencies.py",
            "install_optional_dependencies.py",
            "check_imports.py",
            "check_missing_dependencies.py",
            "save_workspace.py",
            "quick_save.py",
            "workspace_management.py",
            "WORKSPACE_SAVE_GUIDE.md"
        ]
        
        copied = 0
        for file in template_files:
            if os.path.exists(file):
                try:
                    shutil.copy2(file, target_path)
                    copied += 1
                except Exception as e:
                    print(f"⚠️ Could not copy {file}: {e}")
        
        print(f"📄 Copied {copied} template files")
    
    def backup_current_workspace(self, backup_name=None):
        """Backup current workspace before switching"""
        if backup_name is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"workspace_backup_{timestamp}"
        
        print(f"💾 Backing up current workspace: {backup_name}")
        
        try:
            # Use the save_workspace.py script if available
            if os.path.exists("save_workspace.py"):
                subprocess.run([sys.executable, "save_workspace.py"], input="1\n", text=True)
                print("✅ Backup completed using save_workspace.py")
            else:
                # Simple backup
                backup_path = os.path.join(os.path.dirname(os.getcwd()), backup_name)
                shutil.copytree(".", backup_path, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "venv"))
                print(f"✅ Backup created: {backup_path}")
                
        except Exception as e:
            print(f"⚠️ Backup failed: {e}")
    
    def show_workspace_info(self, name):
        """Show detailed information about a workspace"""
        if name not in self.workspaces:
            print(f"❌ Workspace not found: {name}")
            return
        
        info = self.workspaces[name]
        print(f"📁 Workspace: {name}")
        print("=" * 40)
        print(f"📍 Path: {info['path']}")
        print(f"📝 Description: {info['description']}")
        print(f"📅 Created: {info['created']}")
        print(f"🕒 Last used: {info['last_used']}")
        
        # Check if workspace exists
        if os.path.exists(info['path']):
            print(f"✅ Status: Exists")
            
            # Count files
            try:
                files = list(Path(info['path']).glob("*.py"))
                print(f"📄 Python files: {len(files)}")
                
                # Check for key files
                key_files = ["tradingbot_new.py", "requirements.txt", "config.json"]
                for file in key_files:
                    if os.path.exists(os.path.join(info['path'], file)):
                        print(f"✅ {file}")
                    else:
                        print(f"❌ {file}")
                        
            except Exception as e:
                print(f"⚠️ Could not analyze workspace: {e}")
        else:
            print(f"❌ Status: Path does not exist")

def main():
    manager = WorkspaceManager()
    
    if len(sys.argv) < 2:
        print("🏠 Trading Bot Workspace Manager")
        print("=" * 50)
        print("\nUsage:")
        print("  python workspace_management.py list                    - List all workspaces")
        print("  python workspace_management.py add <name> <path>       - Add workspace")
        print("  python workspace_management.py remove <name>           - Remove workspace")
        print("  python workspace_management.py switch <name>           - Switch to workspace")
        print("  python workspace_management.py create <name> [path]    - Create new workspace")
        print("  python workspace_management.py info <name>             - Show workspace info")
        print("  python workspace_management.py backup [name]           - Backup current workspace")
        print("  python workspace_management.py interactive             - Interactive mode")
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        manager.list_workspaces()
    
    elif command == "add" and len(sys.argv) >= 4:
        name = sys.argv[2]
        path = sys.argv[3]
        description = sys.argv[4] if len(sys.argv) > 4 else ""
        manager.add_workspace(name, path, description)
    
    elif command == "remove" and len(sys.argv) >= 3:
        name = sys.argv[2]
        manager.remove_workspace(name)
    
    elif command == "switch" and len(sys.argv) >= 3:
        name = sys.argv[2]
        manager.switch_workspace(name)
    
    elif command == "create" and len(sys.argv) >= 3:
        name = sys.argv[2]
        path = sys.argv[3] if len(sys.argv) > 3 else None
        manager.create_new_workspace(name, path)
    
    elif command == "info" and len(sys.argv) >= 3:
        name = sys.argv[2]
        manager.show_workspace_info(name)
    
    elif command == "backup":
        backup_name = sys.argv[2] if len(sys.argv) > 2 else None
        manager.backup_current_workspace(backup_name)
    
    elif command == "interactive":
        interactive_mode(manager)
    
    else:
        print("❌ Invalid command or missing arguments")
        print("Run without arguments to see usage")

def interactive_mode(manager):
    """Interactive workspace management"""
    print("🏠 Interactive Workspace Manager")
    print("=" * 40)
    
    while True:
        print("\nOptions:")
        print("1. List workspaces")
        print("2. Add workspace")
        print("3. Remove workspace")
        print("4. Switch workspace")
        print("5. Create new workspace")
        print("6. Show workspace info")
        print("7. Backup current workspace")
        print("8. Exit")
        
        choice = input("\nEnter choice (1-8): ").strip()
        
        if choice == "1":
            manager.list_workspaces()
        
        elif choice == "2":
            name = input("Workspace name: ").strip()
            path = input("Workspace path: ").strip()
            description = input("Description (optional): ").strip()
            manager.add_workspace(name, path, description)
        
        elif choice == "3":
            name = input("Workspace name to remove: ").strip()
            manager.remove_workspace(name)
        
        elif choice == "4":
            name = input("Workspace name to switch to: ").strip()
            manager.switch_workspace(name)
        
        elif choice == "5":
            name = input("New workspace name: ").strip()
            path = input("Base path (optional): ").strip()
            if not path:
                path = None
            manager.create_new_workspace(name, path)
        
        elif choice == "6":
            name = input("Workspace name: ").strip()
            manager.show_workspace_info(name)
        
        elif choice == "7":
            backup_name = input("Backup name (optional): ").strip()
            if not backup_name:
                backup_name = None
            manager.backup_current_workspace(backup_name)
        
        elif choice == "8":
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()