"""
Data Manager Agent
Comprehensive filesystem organization for training data, historical data, and ML models
"""

import os
import shutil
import json
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import threading
from pathlib import Path

from agents.base_agent import BaseAgent


class DataManagerAgent(BaseAgent):
    """
    Data Manager Agent - Comprehensive filesystem organization
    Prevents directory flooding with proper data structure management
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("data_manager", config)
        
        # Data organization configuration
        self.base_data_directory = config.get('base_data_directory', 'trading_data')
        self.auto_cleanup = config.get('auto_cleanup', True)
        self.max_file_age_days = config.get('max_file_age_days', 30)
        self.compression_enabled = config.get('compression_enabled', True)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Directory structure
        self.directory_structure = self.define_directory_structure()
        
        # File management
        self.file_registry = {}
        self.cleanup_schedule = {}
        
        # Thread safety
        self.file_lock = threading.Lock()
        
        # Initialize directory structure
        self.create_directory_structure()
        
        self.logger.info(f"Data Manager Agent initialized - Organized filesystem structure created")
    
    def define_directory_structure(self) -> Dict[str, str]:
        """Define comprehensive directory structure for organized data storage"""
        base_dir = self.base_data_directory
        
        return {
            # Historical market data
            'historical_data': f'{base_dir}/historical_data',
            'historical_forex': f'{base_dir}/historical_data/forex',
            'historical_crypto': f'{base_dir}/historical_data/crypto',
            'historical_cache': f'{base_dir}/historical_data/cache',
            
            # Real-time market data
            'realtime_data': f'{base_dir}/realtime_data',
            'tick_data': f'{base_dir}/realtime_data/tick_data',
            'quote_data': f'{base_dir}/realtime_data/quotes',
            'ohlcv_data': f'{base_dir}/realtime_data/ohlcv',
            
            # ML training data
            'ml_training': f'{base_dir}/ml_training',
            'training_features': f'{base_dir}/ml_training/features',
            'training_labels': f'{base_dir}/ml_training/labels',
            'training_datasets': f'{base_dir}/ml_training/datasets',
            'feature_engineering': f'{base_dir}/ml_training/feature_engineering',
            
            # ML models
            'ml_models': f'{base_dir}/ml_models',
            'trained_models': f'{base_dir}/ml_models/trained',
            'model_checkpoints': f'{base_dir}/ml_models/checkpoints',
            'model_metadata': f'{base_dir}/ml_models/metadata',
            'ensemble_models': f'{base_dir}/ml_models/ensemble',
            
            # Backtesting data
            'backtesting': f'{base_dir}/backtesting',
            'backtest_results': f'{base_dir}/backtesting/results',
            'backtest_datasets': f'{base_dir}/backtesting/datasets',
            'parameter_optimization': f'{base_dir}/backtesting/parameter_optimization',
            'walk_forward_results': f'{base_dir}/backtesting/walk_forward',
            
            # Agent data and logs
            'agent_data': f'{base_dir}/agent_data',
            'agent_signals': f'{base_dir}/agent_data/signals',
            'agent_performance': f'{base_dir}/agent_data/performance',
            'confluence_data': f'{base_dir}/agent_data/confluence',
            
            # System logs and monitoring
            'system_logs': f'{base_dir}/system_logs',
            'performance_logs': f'{base_dir}/system_logs/performance',
            'error_logs': f'{base_dir}/system_logs/errors',
            'trading_logs': f'{base_dir}/system_logs/trading',
            
            # Configuration and settings
            'config': f'{base_dir}/config',
            'agent_configs': f'{base_dir}/config/agents',
            'market_configs': f'{base_dir}/config/markets',
            'optimization_configs': f'{base_dir}/config/optimization',
            
            # Exports and reports
            'exports': f'{base_dir}/exports',
            'reports': f'{base_dir}/exports/reports',
            'analysis_exports': f'{base_dir}/exports/analysis',
            'ml_exports': f'{base_dir}/exports/ml_results',
            
            # Temporary and cache
            'temp': f'{base_dir}/temp',
            'cache': f'{base_dir}/cache',
            'downloads': f'{base_dir}/downloads'
        }
    
    def create_directory_structure(self):
        """Create the complete directory structure"""
        created_dirs = []
        
        for dir_name, dir_path in self.directory_structure.items():
            try:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
                created_dirs.append(dir_path)
                
                # Create .gitkeep files to preserve empty directories in git
                gitkeep_path = Path(dir_path) / '.gitkeep'
                if not gitkeep_path.exists():
                    gitkeep_path.touch()
                
            except Exception as e:
                self.logger.error(f"Error creating directory {dir_path}: {e}")
        
        self.logger.info(f"Created {len(created_dirs)} directories for organized data storage")
        
        # Create README files for major directories
        self.create_directory_documentation()
    
    def create_directory_documentation(self):
        """Create README files explaining directory purposes"""
        directory_docs = {
            'historical_data': "Historical market data storage (OHLCV, indicators)\n- forex/: 50-year forex data (1975+)\n- crypto/: 16-year crypto data (2009+)\n- cache/: Processed data cache",
            'ml_training': "ML training data and features\n- features/: Engineered features from all agents\n- labels/: Trade outcomes and targets\n- datasets/: Complete training datasets",
            'ml_models': "Trained ML models and ensembles\n- trained/: Final trained models\n- checkpoints/: Training checkpoints\n- ensemble/: Ensemble model combinations",
            'backtesting': "Backtesting results and analysis\n- results/: Individual backtest results\n- parameter_optimization/: Parameter sweep results\n- walk_forward/: Walk-forward analysis results",
            'agent_data': "Agent signals and performance data\n- signals/: Real-time agent signals\n- performance/: Agent performance metrics\n- confluence/: Pattern confluence data",
            'system_logs': "System logging and monitoring\n- performance/: System performance logs\n- errors/: Error logs and recovery\n- trading/: Trade execution logs"
        }
        
        for dir_key, description in directory_docs.items():
            if dir_key in self.directory_structure:
                readme_path = Path(self.directory_structure[dir_key]) / 'README.md'
                try:
                    with open(readme_path, 'w') as f:
                        f.write(f"# {dir_key.replace('_', ' ').title()}\n\n{description}\n")
                except Exception as e:
                    self.logger.warning(f"Could not create README for {dir_key}: {e}")
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data management requests
        
        Args:
            data: Dictionary containing data management request
            
        Returns:
            Dictionary with data management results
        """
        try:
            action = data.get('action', 'organize_data')
            
            if action == 'organize_data':
                return self.organize_data_files(data)
            elif action == 'save_historical_data':
                return self.save_historical_data(data)
            elif action == 'save_ml_data':
                return self.save_ml_training_data(data)
            elif action == 'save_model':
                return self.save_ml_model(data)
            elif action == 'save_backtest_results':
                return self.save_backtest_results(data)
            elif action == 'cleanup_old_files':
                return self.cleanup_old_files(data)
            elif action == 'get_storage_status':
                return self.get_storage_status()
            else:
                return {'error': f'Unknown data management action: {action}'}
                
        except Exception as e:
            self.logger.error(f"Error in data management: {e}")
            return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}
    
    def save_historical_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save historical data with proper organization
        """
        required_fields = ['symbol', 'timeframe', 'data']
        if not self.validate_data(data, required_fields):
            return {'error': 'Missing required fields for historical data save'}
        
        symbol = data['symbol']
        timeframe = data['timeframe']
        df = data['data']
        
        # Determine market type and directory
        if self.market_type == 'forex':
            base_dir = self.directory_structure['historical_forex']
        else:
            base_dir = self.directory_structure['historical_crypto']
        
        # Create organized file path
        safe_symbol = symbol.replace('/', '_')
        filename = f"{safe_symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d')}.parquet"
        file_path = Path(base_dir) / safe_symbol / filename
        
        # Create symbol directory if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with self.file_lock:
                # Save as compressed parquet for efficiency
                df.to_parquet(file_path, compression='gzip')
                
                # Update file registry
                self.file_registry[str(file_path)] = {
                    'type': 'historical_data',
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'created': datetime.now(timezone.utc),
                    'size_mb': file_path.stat().st_size / (1024 * 1024),
                    'records': len(df)
                }
            
            self.logger.info(f"Saved historical data: {symbol} {timeframe} ({len(df)} records) -> {file_path}")
            
            return {
                'success': True,
                'file_path': str(file_path),
                'records_saved': len(df),
                'file_size_mb': self.file_registry[str(file_path)]['size_mb']
            }
            
        except Exception as e:
            self.logger.error(f"Error saving historical data for {symbol} {timeframe}: {e}")
            return {'error': str(e)}
    
    def save_ml_training_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save ML training data with proper organization
        """
        required_fields = ['features', 'labels', 'dataset_name']
        if not self.validate_data(data, required_fields):
            return {'error': 'Missing required fields for ML data save'}
        
        features = data['features']
        labels = data['labels']
        dataset_name = data['dataset_name']
        metadata = data.get('metadata', {})
        
        # Create organized file paths
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        features_path = Path(self.directory_structure['training_features']) / f"{dataset_name}_features_{timestamp}.parquet"
        labels_path = Path(self.directory_structure['training_labels']) / f"{dataset_name}_labels_{timestamp}.parquet"
        metadata_path = Path(self.directory_structure['training_datasets']) / f"{dataset_name}_metadata_{timestamp}.json"
        
        try:
            with self.file_lock:
                # Save features
                if isinstance(features, pd.DataFrame):
                    features.to_parquet(features_path, compression='gzip')
                else:
                    pd.DataFrame(features).to_parquet(features_path, compression='gzip')
                
                # Save labels
                if isinstance(labels, pd.DataFrame):
                    labels.to_parquet(labels_path, compression='gzip')
                else:
                    pd.DataFrame(labels).to_parquet(labels_path, compression='gzip')
                
                # Save metadata
                complete_metadata = {
                    'dataset_name': dataset_name,
                    'created': datetime.now(timezone.utc).isoformat(),
                    'features_path': str(features_path),
                    'labels_path': str(labels_path),
                    'features_shape': features.shape if hasattr(features, 'shape') else len(features),
                    'labels_shape': labels.shape if hasattr(labels, 'shape') else len(labels),
                    'market_type': self.market_type,
                    **metadata
                }
                
                with open(metadata_path, 'w') as f:
                    json.dump(complete_metadata, f, indent=2)
                
                # Update registry
                self.file_registry[str(features_path)] = {
                    'type': 'ml_features',
                    'dataset_name': dataset_name,
                    'created': datetime.now(timezone.utc),
                    'size_mb': features_path.stat().st_size / (1024 * 1024)
                }
            
            self.logger.info(f"Saved ML training data: {dataset_name} -> {features_path.parent}")
            
            return {
                'success': True,
                'features_path': str(features_path),
                'labels_path': str(labels_path),
                'metadata_path': str(metadata_path),
                'dataset_info': complete_metadata
            }
            
        except Exception as e:
            self.logger.error(f"Error saving ML training data {dataset_name}: {e}")
            return {'error': str(e)}
    
    def save_ml_model(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save ML model with proper organization
        """
        required_fields = ['model', 'model_name', 'model_type']
        if not self.validate_data(data, required_fields):
            return {'error': 'Missing required fields for model save'}
        
        model = data['model']
        model_name = data['model_name']
        model_type = data['model_type']
        performance_metrics = data.get('performance_metrics', {})
        
        # Create organized model path
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_dir = Path(self.directory_structure['trained_models']) / model_type / model_name
        model_dir.mkdir(parents=True, exist_ok=True)
        
        model_path = model_dir / f"{model_name}_{timestamp}.joblib"
        metadata_path = model_dir / f"{model_name}_{timestamp}_metadata.json"
        
        try:
            with self.file_lock:
                # Save model
                import joblib
                joblib.dump(model, model_path)
                
                # Save metadata
                model_metadata = {
                    'model_name': model_name,
                    'model_type': model_type,
                    'created': datetime.now(timezone.utc).isoformat(),
                    'model_path': str(model_path),
                    'performance_metrics': performance_metrics,
                    'market_type': self.market_type,
                    'file_size_mb': model_path.stat().st_size / (1024 * 1024)
                }
                
                with open(metadata_path, 'w') as f:
                    json.dump(model_metadata, f, indent=2)
                
                # Update registry
                self.file_registry[str(model_path)] = {
                    'type': 'ml_model',
                    'model_name': model_name,
                    'model_type': model_type,
                    'created': datetime.now(timezone.utc),
                    'size_mb': model_metadata['file_size_mb']
                }
            
            self.logger.info(f"Saved ML model: {model_name} ({model_type}) -> {model_path}")
            
            return {
                'success': True,
                'model_path': str(model_path),
                'metadata_path': str(metadata_path),
                'model_info': model_metadata
            }
            
        except Exception as e:
            self.logger.error(f"Error saving ML model {model_name}: {e}")
            return {'error': str(e)}
    
    def save_backtest_results(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save backtest results with proper organization
        """
        required_fields = ['results', 'backtest_name']
        if not self.validate_data(data, required_fields):
            return {'error': 'Missing required fields for backtest save'}
        
        results = data['results']
        backtest_name = data['backtest_name']
        symbol = data.get('symbol', 'unknown')
        timeframe = data.get('timeframe', 'unknown')
        
        # Create organized backtest path
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backtest_dir = Path(self.directory_structure['backtest_results']) / f"{backtest_name}_{timestamp}"
        backtest_dir.mkdir(parents=True, exist_ok=True)
        
        results_path = backtest_dir / 'results.json'
        summary_path = backtest_dir / 'summary.json'
        
        try:
            with self.file_lock:
                # Save full results
                with open(results_path, 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                
                # Save summary
                summary = {
                    'backtest_name': backtest_name,
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'created': datetime.now(timezone.utc).isoformat(),
                    'market_type': self.market_type,
                    'results_path': str(results_path),
                    'total_trades': results.get('total_trades', 0),
                    'win_rate': results.get('win_rate', 0),
                    'total_return': results.get('total_return', 0)
                }
                
                with open(summary_path, 'w') as f:
                    json.dump(summary, f, indent=2)
                
                # Update registry
                self.file_registry[str(results_path)] = {
                    'type': 'backtest_results',
                    'backtest_name': backtest_name,
                    'symbol': symbol,
                    'created': datetime.now(timezone.utc),
                    'size_mb': results_path.stat().st_size / (1024 * 1024)
                }
            
            self.logger.info(f"Saved backtest results: {backtest_name} -> {backtest_dir}")
            
            return {
                'success': True,
                'results_path': str(results_path),
                'summary_path': str(summary_path),
                'backtest_dir': str(backtest_dir)
            }
            
        except Exception as e:
            self.logger.error(f"Error saving backtest results {backtest_name}: {e}")
            return {'error': str(e)}
    
    def organize_data_files(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Organize existing data files into proper structure
        """
        source_directory = data.get('source_directory', '.')
        
        organized_files = {
            'moved': 0,
            'organized': 0,
            'errors': 0,
            'summary': {}
        }
        
        try:
            # Find and organize different file types
            for root, dirs, files in os.walk(source_directory):
                for file in files:
                    file_path = Path(root) / file
                    
                    try:
                        if self.should_organize_file(file_path):
                            new_location = self.determine_file_location(file_path)
                            if new_location:
                                self.move_file_to_organized_location(file_path, new_location)
                                organized_files['moved'] += 1
                    
                    except Exception as e:
                        self.logger.warning(f"Error organizing file {file_path}: {e}")
                        organized_files['errors'] += 1
            
            organized_files['organized'] = organized_files['moved']
            
            return {
                'agent_id': self.agent_id,
                'organization_completed': True,
                'organized_files': organized_files,
                'directory_structure': self.directory_structure
            }
            
        except Exception as e:
            self.logger.error(f"Error organizing data files: {e}")
            return {'error': str(e)}
    
    def should_organize_file(self, file_path: Path) -> bool:
        """Determine if file should be organized"""
        file_extensions_to_organize = [
            '.csv', '.parquet', '.json', '.pkl', '.joblib',
            '.h5', '.hdf5', '.feather', '.xlsx'
        ]
        
        return file_path.suffix.lower() in file_extensions_to_organize
    
    def determine_file_location(self, file_path: Path) -> Optional[str]:
        """Determine where file should be moved"""
        filename = file_path.name.lower()
        
        # Historical data files
        if any(term in filename for term in ['ohlcv', 'historical', 'price_data']):
            if any(pair in filename for pair in ['eur_usd', 'gbp_usd', 'usd_jpy']):
                return self.directory_structure['historical_forex']
            else:
                return self.directory_structure['historical_crypto']
        
        # ML model files
        elif any(term in filename for term in ['model', 'xgboost', 'lstm', 'ensemble']):
            return self.directory_structure['trained_models']
        
        # Training data files
        elif any(term in filename for term in ['features', 'training', 'labels']):
            return self.directory_structure['training_datasets']
        
        # Backtest result files
        elif any(term in filename for term in ['backtest', 'results', 'performance']):
            return self.directory_structure['backtest_results']
        
        return None
    
    def move_file_to_organized_location(self, source_path: Path, target_directory: str):
        """Move file to organized location"""
        target_path = Path(target_directory) / source_path.name
        
        # Create target directory if needed
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Move file
        shutil.move(str(source_path), str(target_path))
        
        self.logger.debug(f"Moved {source_path} -> {target_path}")
    
    def cleanup_old_files(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cleanup old files to prevent directory flooding
        """
        max_age_days = data.get('max_age_days', self.max_file_age_days)
        cutoff_date = datetime.now(timezone.utc) - pd.Timedelta(days=max_age_days)
        
        cleanup_results = {
            'files_deleted': 0,
            'space_freed_mb': 0.0,
            'directories_cleaned': 0
        }
        
        try:
            # Clean temporary files
            temp_dir = Path(self.directory_structure['temp'])
            if temp_dir.exists():
                cleanup_results.update(self.cleanup_directory(temp_dir, cutoff_date))
            
            # Clean old cache files
            cache_dir = Path(self.directory_structure['cache'])
            if cache_dir.exists():
                cache_cleanup = self.cleanup_directory(cache_dir, cutoff_date)
                cleanup_results['files_deleted'] += cache_cleanup['files_deleted']
                cleanup_results['space_freed_mb'] += cache_cleanup['space_freed_mb']
            
            # Clean old log files (keep recent ones)
            log_cutoff = datetime.now(timezone.utc) - pd.Timedelta(days=7)  # Keep 1 week of logs
            logs_dir = Path(self.directory_structure['system_logs'])
            if logs_dir.exists():
                log_cleanup = self.cleanup_directory(logs_dir, log_cutoff)
                cleanup_results['files_deleted'] += log_cleanup['files_deleted']
                cleanup_results['space_freed_mb'] += log_cleanup['space_freed_mb']
            
            self.logger.info(f"Cleanup completed: {cleanup_results['files_deleted']} files deleted, "
                           f"{cleanup_results['space_freed_mb']:.2f} MB freed")
            
            return {
                'agent_id': self.agent_id,
                'cleanup_completed': True,
                'cleanup_results': cleanup_results,
                'cutoff_date': cutoff_date.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            return {'error': str(e)}
    
    def cleanup_directory(self, directory: Path, cutoff_date: datetime) -> Dict[str, Any]:
        """Cleanup files in specific directory"""
        cleanup_stats = {'files_deleted': 0, 'space_freed_mb': 0.0}
        
        if not directory.exists():
            return cleanup_stats
        
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                try:
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
                    
                    if file_mtime < cutoff_date:
                        file_size_mb = file_path.stat().st_size / (1024 * 1024)
                        file_path.unlink()
                        
                        cleanup_stats['files_deleted'] += 1
                        cleanup_stats['space_freed_mb'] += file_size_mb
                        
                        # Remove from registry
                        self.file_registry.pop(str(file_path), None)
                
                except Exception as e:
                    self.logger.warning(f"Error deleting file {file_path}: {e}")
        
        return cleanup_stats
    
    def get_storage_status(self) -> Dict[str, Any]:
        """Get comprehensive storage status"""
        storage_status = {
            'directory_structure': self.directory_structure,
            'file_registry_count': len(self.file_registry),
            'storage_usage': {},
            'directory_sizes': {}
        }
        
        # Calculate directory sizes
        for dir_name, dir_path in self.directory_structure.items():
            try:
                if Path(dir_path).exists():
                    total_size = sum(f.stat().st_size for f in Path(dir_path).rglob('*') if f.is_file())
                    storage_status['directory_sizes'][dir_name] = {
                        'size_mb': total_size / (1024 * 1024),
                        'file_count': len(list(Path(dir_path).rglob('*'))) if Path(dir_path).exists() else 0
                    }
            except Exception as e:
                storage_status['directory_sizes'][dir_name] = {'error': str(e)}
        
        # Calculate total storage usage
        total_size_mb = sum(
            dir_info.get('size_mb', 0) for dir_info in storage_status['directory_sizes'].values()
            if isinstance(dir_info, dict) and 'size_mb' in dir_info
        )
        
        storage_status['storage_usage'] = {
            'total_size_mb': total_size_mb,
            'total_size_gb': total_size_mb / 1024,
            'largest_directory': max(
                storage_status['directory_sizes'].items(),
                key=lambda x: x[1].get('size_mb', 0) if isinstance(x[1], dict) else 0
            )[0] if storage_status['directory_sizes'] else 'none'
        }
        
        return storage_status
    
    def get_signal_strength(self) -> float:
        """Get signal strength based on data organization health"""
        if not self.file_registry:
            return 1.0  # Perfect when no files to manage
        
        # Signal strength based on organization efficiency
        total_files = len(self.file_registry)
        organized_files = sum(1 for info in self.file_registry.values() if info.get('type') != 'unknown')
        
        organization_ratio = organized_files / total_files if total_files > 0 else 1.0
        
        return organization_ratio
    
    def requires_continuous_processing(self) -> bool:
        """Data manager benefits from continuous processing for cleanup"""
        return True
    
    def _continuous_process(self):
        """Continuous processing for data management"""
        try:
            # Perform periodic cleanup if enabled
            if self.auto_cleanup:
                cleanup_result = self.cleanup_old_files({})
                if cleanup_result.get('cleanup_results', {}).get('files_deleted', 0) > 0:
                    self.logger.info(f"Auto-cleanup: {cleanup_result['cleanup_results']['files_deleted']} files removed")
        
        except Exception as e:
            self.logger.error(f"Error in data manager continuous processing: {e}")
    
    def get_processing_interval(self) -> float:
        """Get processing interval for cleanup"""
        return 3600.0  # Check every hour for cleanup