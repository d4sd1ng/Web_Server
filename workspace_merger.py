#!/usr/bin/env python3
"""
Workspace Merger Script
Merges multiple trading bot workspaces into one unified workspace
"""

import os
import shutil
import json
import datetime
import subprocess
import sys
from pathlib import Path
import glob

class WorkspaceMerger:
    def __init__(self):
        self.current_dir = os.getcwd()
        self.merge_target = self.current_dir
        self.trading_bot_files = []
        self.found_workspaces = []
        
    def find_trading_bot_workspaces(self, search_paths=None):
        """Find all directories containing trading bot files"""
        if search_paths is None:
            # Search common locations
            search_paths = [
                os.path.dirname(self.current_dir),  # Parent directory
                os.path.expanduser("~"),  # Home directory
                "/workspace",
                "/tmp",
                "."
            ]
        
        print("🔍 Searching for trading bot workspaces...")
        
        key_files = [
            "tradingbot_new.py",
            "tradingbot_ict_smc.py", 
            "ml_tradingbot.py",
            "ict_smc_enhancement.py",
            "tradingbot_enhanced_bos_choch.py"
        ]
        
        for search_path in search_paths:
            if not os.path.exists(search_path):
                continue
                
            print(f"🔍 Searching in: {search_path}")
            
            # Search for trading bot files recursively
            for root, dirs, files in os.walk(search_path):
                # Skip hidden directories and common ignore patterns
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', 'node_modules']]
                
                found_files = []
                for key_file in key_files:
                    if key_file in files:
                        found_files.append(key_file)
                
                if found_files:
                    workspace_info = {
                        'path': root,
                        'files': found_files,
                        'total_py_files': len([f for f in files if f.endswith('.py')])
                    }
                    self.found_workspaces.append(workspace_info)
                    print(f"✅ Found workspace: {root}")
                    print(f"   📄 Key files: {', '.join(found_files)}")
                    print(f"   🐍 Total Python files: {workspace_info['total_py_files']}")
    
    def scan_current_git_repos(self):
        """Scan for git repositories that might contain trading bot code"""
        print("🔍 Scanning for git repositories...")
        
        try:
            # Check if we're in a git repo
            result = subprocess.run(['git', 'remote', '-v'], capture_output=True, text=True, cwd=self.current_dir)
            if result.returncode == 0:
                print("📁 Current directory is a git repository")
                
                # Check for other branches or stashes that might have trading bot files
                branches_result = subprocess.run(['git', 'branch', '-a'], capture_output=True, text=True)
                if branches_result.returncode == 0:
                    branches = branches_result.stdout.strip().split('\n')
                    print(f"🌿 Found {len(branches)} branches")
                    
                    for branch in branches:
                        branch = branch.strip().replace('*', '').strip()
                        if branch and not branch.startswith('remotes/origin/HEAD'):
                            print(f"   • {branch}")
        
        except Exception as e:
            print(f"⚠️ Could not check git status: {e}")
    
    def list_found_workspaces(self):
        """List all found workspaces"""
        if not self.found_workspaces:
            print("❌ No trading bot workspaces found")
            return
        
        print("\n📁 Found Trading Bot Workspaces:")
        print("=" * 60)
        
        for i, workspace in enumerate(self.found_workspaces, 1):
            print(f"{i}. {workspace['path']}")
            print(f"   📄 Key files: {', '.join(workspace['files'])}")
            print(f"   🐍 Total Python files: {workspace['total_py_files']}")
            print()
    
    def merge_workspace(self, source_path, target_path=None):
        """Merge a workspace into the target directory"""
        if target_path is None:
            target_path = self.merge_target
        
        if not os.path.exists(source_path):
            print(f"❌ Source path does not exist: {source_path}")
            return False
        
        if source_path == target_path:
            print(f"⚠️ Source and target are the same: {source_path}")
            return True
        
        print(f"🔄 Merging workspace:")
        print(f"   📂 From: {source_path}")
        print(f"   📂 To: {target_path}")
        
        merged_files = 0
        conflicts = []
        
        try:
            for root, dirs, files in os.walk(source_path):
                # Skip hidden directories and common ignore patterns
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', 'node_modules']]
                
                # Calculate relative path from source
                rel_path = os.path.relpath(root, source_path)
                target_dir = os.path.join(target_path, rel_path) if rel_path != '.' else target_path
                
                # Create target directory if it doesn't exist
                os.makedirs(target_dir, exist_ok=True)
                
                for file in files:
                    if file.endswith(('.pyc', '.pyo')) or file.startswith('.'):
                        continue
                    
                    source_file = os.path.join(root, file)
                    target_file = os.path.join(target_dir, file)
                    
                    # Handle conflicts
                    if os.path.exists(target_file):
                        # Create backup of existing file
                        backup_file = f"{target_file}.backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        shutil.copy2(target_file, backup_file)
                        conflicts.append((file, target_file, backup_file))
                    
                    # Copy file
                    shutil.copy2(source_file, target_file)
                    merged_files += 1
            
            print(f"✅ Merged {merged_files} files")
            
            if conflicts:
                print(f"⚠️ Handled {len(conflicts)} conflicts (backups created):")
                for file, target, backup in conflicts[:5]:  # Show first 5 conflicts
                    print(f"   • {file} -> {backup}")
                if len(conflicts) > 5:
                    print(f"   ... and {len(conflicts) - 5} more")
            
            return True
            
        except Exception as e:
            print(f"❌ Error merging workspace: {e}")
            return False
    
    def merge_all_workspaces(self):
        """Merge all found workspaces into the current directory"""
        if not self.found_workspaces:
            print("❌ No workspaces to merge")
            return
        
        print(f"🎯 Merging all workspaces into: {self.merge_target}")
        
        success_count = 0
        for workspace in self.found_workspaces:
            if self.merge_workspace(workspace['path']):
                success_count += 1
        
        print(f"\n✅ Successfully merged {success_count}/{len(self.found_workspaces)} workspaces")
        
        # Create summary of merged files
        self.create_merge_summary()
    
    def create_merge_summary(self):
        """Create a summary of the merged workspace"""
        print("\n📊 Creating merge summary...")
        
        # Count files by type
        py_files = list(Path(self.merge_target).glob("**/*.py"))
        md_files = list(Path(self.merge_target).glob("**/*.md"))
        json_files = list(Path(self.merge_target).glob("**/*.json"))
        csv_files = list(Path(self.merge_target).glob("**/*.csv"))
        
        # Key trading bot files
        key_files = [
            "tradingbot_new.py",
            "tradingbot_ict_smc.py",
            "ml_tradingbot.py", 
            "ict_smc_enhancement.py",
            "tradingbot_enhanced_bos_choch.py",
            "utils.py",
            "requirements.txt"
        ]
        
        summary = {
            "merge_timestamp": datetime.datetime.now().isoformat(),
            "merge_target": self.merge_target,
            "total_files": {
                "python": len(py_files),
                "markdown": len(md_files),
                "json": len(json_files),
                "csv": len(csv_files)
            },
            "key_files_present": {},
            "merged_workspaces": len(self.found_workspaces)
        }
        
        # Check for key files
        for key_file in key_files:
            file_path = os.path.join(self.merge_target, key_file)
            summary["key_files_present"][key_file] = os.path.exists(file_path)
        
        # Save summary
        with open("workspace_merge_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        # Print summary
        print("\n📋 Workspace Merge Summary:")
        print("=" * 50)
        print(f"🎯 Target Directory: {self.merge_target}")
        print(f"🔄 Merged Workspaces: {summary['merged_workspaces']}")
        print(f"🐍 Python Files: {summary['total_files']['python']}")
        print(f"📝 Markdown Files: {summary['total_files']['markdown']}")
        print(f"📊 JSON Files: {summary['total_files']['json']}")
        print(f"📈 CSV Files: {summary['total_files']['csv']}")
        print()
        print("🔑 Key Trading Bot Files:")
        for key_file, exists in summary["key_files_present"].items():
            status = "✅" if exists else "❌"
            print(f"   {status} {key_file}")
        
        print(f"\n💾 Summary saved to: workspace_merge_summary.json")
    
    def interactive_merge(self):
        """Interactive workspace merger"""
        print("🔄 Interactive Workspace Merger")
        print("=" * 40)
        
        # First, find workspaces
        self.find_trading_bot_workspaces()
        self.scan_current_git_repos()
        
        if not self.found_workspaces:
            print("\n❌ No trading bot workspaces found!")
            print("💡 Try:")
            print("   1. Check if files are in a different location")
            print("   2. Search manually with: find / -name 'tradingbot*.py' 2>/dev/null")
            print("   3. Clone your trading bot repository")
            return
        
        self.list_found_workspaces()
        
        print("\nOptions:")
        print("1. Merge all workspaces automatically")
        print("2. Select specific workspaces to merge")
        print("3. Show workspace details")
        print("4. Exit")
        
        while True:
            choice = input("\nEnter choice (1-4): ").strip()
            
            if choice == "1":
                self.merge_all_workspaces()
                break
            
            elif choice == "2":
                print("\nSelect workspaces to merge (comma-separated numbers):")
                self.list_found_workspaces()
                selection = input("Enter numbers: ").strip()
                
                try:
                    indices = [int(x.strip()) - 1 for x in selection.split(",")]
                    for idx in indices:
                        if 0 <= idx < len(self.found_workspaces):
                            workspace = self.found_workspaces[idx]
                            self.merge_workspace(workspace['path'])
                    
                    self.create_merge_summary()
                    break
                    
                except ValueError:
                    print("❌ Invalid selection")
            
            elif choice == "3":
                self.list_found_workspaces()
            
            elif choice == "4":
                print("👋 Exiting merger")
                break
            
            else:
                print("❌ Invalid choice")

def main():
    merger = WorkspaceMerger()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "find":
            merger.find_trading_bot_workspaces()
            merger.list_found_workspaces()
        
        elif command == "merge":
            merger.find_trading_bot_workspaces()
            merger.merge_all_workspaces()
        
        elif command == "interactive":
            merger.interactive_merge()
        
        else:
            print("❌ Unknown command")
    else:
        # Default to interactive mode
        merger.interactive_merge()

if __name__ == "__main__":
    main()