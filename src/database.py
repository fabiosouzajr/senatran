"""
Database manager for storing fine information.
Handles SQLite database operations with upsert logic.
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from config import DATABASE_CONFIG

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database operations for fine records."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file. If None, uses default from config.
        """
        self.db_path = db_path or DATABASE_CONFIG['path']
        self.connection = None
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """Create database and tables if they don't exist."""
        # Create parent directory if it doesn't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect and create schema
        self.connection = sqlite3.connect(
            str(self.db_path),
            timeout=DATABASE_CONFIG['timeout']
        )
        self.connection.row_factory = sqlite3.Row  # Enable column access by name
        
        cursor = self.connection.cursor()
        
        # Create fines table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fines (
                renainf TEXT PRIMARY KEY,
                vehicle_plate TEXT,
                orgao_autuador TEXT,
                orgao_competente TEXT,
                local_infracao TEXT,
                data_hora_cometimento TEXT,
                numero_auto TEXT,
                codigo_infracao TEXT,
                valor_original TEXT,
                data_notificacao_autuacao TEXT,
                data_limite_defesa_previa TEXT,
                data_limite_identificacao_condutor TEXT,
                data_notificacao_penalidade TEXT,
                data_limite_recurso TEXT,
                data_vencimento_desconto TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index on vehicle_plate for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_vehicle_plate 
            ON fines(vehicle_plate)
        """)
        
        self.connection.commit()
        logger.info(f"Database initialized at {self.db_path}")
    
    def upsert_fine(self, fine_data: Dict[str, str]) -> bool:
        """
        Insert or update a fine record.
        
        Args:
            fine_data: Dictionary containing fine information.
                     Must include 'renainf' as primary key.
        
        Returns:
            True if successful, False otherwise.
        """
        if 'renainf' not in fine_data:
            logger.error("Fine data must include 'renainf' field")
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # Use INSERT OR REPLACE for upsert
            cursor.execute("""
                INSERT OR REPLACE INTO fines (
                    renainf, vehicle_plate, orgao_autuador, orgao_competente,
                    local_infracao, data_hora_cometimento, numero_auto,
                    codigo_infracao, valor_original, data_notificacao_autuacao,
                    data_limite_defesa_previa, data_limite_identificacao_condutor,
                    data_notificacao_penalidade, data_limite_recurso,
                    data_vencimento_desconto, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fine_data.get('renainf'),
                fine_data.get('vehicle_plate'),
                fine_data.get('orgao_autuador'),
                fine_data.get('orgao_competente'),
                fine_data.get('local_infracao'),
                fine_data.get('data_hora_cometimento'),
                fine_data.get('numero_auto'),
                fine_data.get('codigo_infracao'),
                fine_data.get('valor_original'),
                fine_data.get('data_notificacao_autuacao'),
                fine_data.get('data_limite_defesa_previa'),
                fine_data.get('data_limite_identificacao_condutor'),
                fine_data.get('data_notificacao_penalidade'),
                fine_data.get('data_limite_recurso'),
                fine_data.get('data_vencimento_desconto'),
                datetime.now().isoformat()
            ))
            
            self.connection.commit()
            logger.debug(f"Upserted fine with RENAINF: {fine_data.get('renainf')}")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Database error while upserting fine: {e}")
            self.connection.rollback()
            return False
    
    def upsert_fines_batch(self, fines_data: List[Dict[str, str]]) -> int:
        """
        Insert or update multiple fine records in a batch.
        
        Args:
            fines_data: List of dictionaries containing fine information.
        
        Returns:
            Number of successfully upserted records.
        """
        success_count = 0
        for fine_data in fines_data:
            if self.upsert_fine(fine_data):
                success_count += 1
        logger.info(f"Batch upserted {success_count}/{len(fines_data)} fines")
        return success_count
    
    def get_fine_by_renainf(self, renainf: str) -> Optional[Dict[str, str]]:
        """
        Retrieve a fine record by RENAINF.
        
        Args:
            renainf: RENAINF number to search for.
        
        Returns:
            Dictionary with fine data or None if not found.
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM fines WHERE renainf = ?", (renainf,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
            
        except sqlite3.Error as e:
            logger.error(f"Database error while retrieving fine: {e}")
            return None
    
    def get_fines_by_vehicle(self, vehicle_plate: str) -> List[Dict[str, str]]:
        """
        Retrieve all fines for a specific vehicle.
        
        Args:
            vehicle_plate: Vehicle plate to search for.
        
        Returns:
            List of dictionaries with fine data.
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "SELECT * FROM fines WHERE vehicle_plate = ? ORDER BY data_hora_cometimento",
                (vehicle_plate,)
            )
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
        except sqlite3.Error as e:
            logger.error(f"Database error while retrieving vehicle fines: {e}")
            return []
    
    def get_all_fines(self) -> List[Dict[str, str]]:
        """
        Retrieve all fine records.
        
        Returns:
            List of dictionaries with fine data.
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM fines ORDER BY vehicle_plate, data_hora_cometimento")
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
        except sqlite3.Error as e:
            logger.error(f"Database error while retrieving all fines: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with statistics (total fines, unique vehicles, etc.)
        """
        try:
            cursor = self.connection.cursor()
            
            stats = {}
            
            # Total fines
            cursor.execute("SELECT COUNT(*) FROM fines")
            stats['total_fines'] = cursor.fetchone()[0]
            
            # Unique vehicles
            cursor.execute("SELECT COUNT(DISTINCT vehicle_plate) FROM fines")
            stats['unique_vehicles'] = cursor.fetchone()[0]
            
            # Fines per vehicle
            cursor.execute("""
                SELECT vehicle_plate, COUNT(*) as count 
                FROM fines 
                GROUP BY vehicle_plate 
                ORDER BY count DESC
            """)
            stats['fines_per_vehicle'] = dict(cursor.fetchall())
            
            return stats
            
        except sqlite3.Error as e:
            logger.error(f"Database error while getting statistics: {e}")
            return {}
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()



