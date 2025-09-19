import platform
import os
import subprocess
import logging
import shutil
from datetime import datetime
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.version import __version__
from app.security.user_security import get_current_user
from app.schemas.user_schema import User
from app.repositories.settings import settings

system_Router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BACKUP_DIR = settings.BACKUP_DIR
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

def run_backup(db_settings: dict, backup_filepath: str):
    """
    Function to be run in the background to create a database backup.
    """
    logger.info(f"Starting database backup to {backup_filepath}...")
    env = os.environ.copy()
    env["PGPASSWORD"] = db_settings["password"]

    command = [
        "pg_dump",
        "-h", db_settings["host"],
        "-p", str(db_settings["port"]),
        "-U", db_settings["user"],
        "-d", db_settings["db"],
        "-F", "c",  # Custom format, compressed
        "-f", backup_filepath,
    ]

    try:
        process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            logger.info(f"Database backup successful: {backup_filepath}")
        else:
            logger.error(f"Database backup failed. Error: {stderr.decode()}")
    except Exception as e:
        logger.error(f"An exception occurred during backup: {e}")


def run_restore(db_settings: dict, backup_filepath: str):
    """
    Function to be run in the background to restore the database.
    """
    logger.info(f"Starting database restore from {backup_filepath}...")
    env = os.environ.copy()
    env["PGPASSWORD"] = db_settings["password"]
    
    psql_command_base = [
        "psql",
        "-h", db_settings["host"],
        "-p", str(db_settings["port"]),
        "-U", db_settings["user"],
    ]

    try:
        logger.info(f"Connecting to 'postgres' database to manage '{db_settings['db']}'...")
        
        term_connections_sql = f"SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '{db_settings['db']}' AND pid <> pg_backend_pid();"
        subprocess.run(psql_command_base + ["-d", "postgres", "-c", term_connections_sql], env=env, check=True, capture_output=True)
        logger.info(f"Terminated active connections to '{db_settings['db']}'.")

        drop_db_sql = f"DROP DATABASE IF EXISTS \"{db_settings['db']}\";"
        subprocess.run(psql_command_base + ["-d", "postgres", "-c", drop_db_sql], env=env, check=True, capture_output=True)
        logger.info(f"Dropped database '{db_settings['db']}'.")

        create_db_sql = f"CREATE DATABASE \"{db_settings['db']}\" WITH OWNER = \"{db_settings['user']}\";"
        subprocess.run(psql_command_base + ["-d", "postgres", "-c", create_db_sql], env=env, check=True, capture_output=True)
        logger.info(f"Created database '{db_settings['db']}'.")

        logger.info(f"Restoring data to '{db_settings['db']}'...")
        restore_command = [
            "pg_restore",
            "-h", db_settings["host"],
            "-p", str(db_settings["port"]),
            "-U", db_settings["user"],
            "-d", db_settings["db"],
            "--clean",
            "--if-exists",
            backup_filepath,
        ]
        
        process = subprocess.Popen(restore_command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            logger.info("Database restore successful.")
        else:
            logger.error(f"Database restore failed. Error: {stderr.decode()}")
            if stdout:
                logger.error(f"Restore stdout: {stdout.decode()}")

    except subprocess.CalledProcessError as e:
        logger.error(f"A subprocess error occurred during restore setup: {e.stderr.decode()}")
    except Exception as e:
        logger.error(f"An exception occurred during restore: {e}")


@system_Router.get("/sysinfo", tags=["system"])
async def get_sysinfo():
    return {
        "api_version": __version__,
        "python_version": platform.python_version(),
    }

@system_Router.post("/system/upload-backup", tags=["system"])
async def upload_backup_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads a database backup file to the server.
    """
    if not file.filename.endswith(".dump"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type. Only .dump files are allowed.")

    safe_filename = os.path.basename(file.filename)
    if not safe_filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename.")

    destination_path = os.path.join(BACKUP_DIR, safe_filename)

    if os.path.exists(destination_path):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"File '{safe_filename}' already exists. Please delete the existing file or rename your upload.")

    try:
        with open(destination_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save uploaded file: {e}")
    finally:
        file.file.close()

    return {"message": "File uploaded successfully", "filename": safe_filename}

@system_Router.post("/system/backup", status_code=status.HTTP_202_ACCEPTED, tags=["system"])
async def create_backup(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Triggers a database backup task to run in the background.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_filename = f"cashio_backup_{timestamp}.dump"
    backup_filepath = os.path.join(BACKUP_DIR, backup_filename)

    db_settings = {
        "host": settings.POSTGRES_HOST,
        "port": settings.POSTGRES_PORT,
        "user": settings.POSTGRES_USER,
        "password": settings.POSTGRES_PASSWORD,
        "db": settings.POSTGRES_DB,
    }

    background_tasks.add_task(run_backup, db_settings, backup_filepath)

    return {"message": "Database backup process started.", "filename": backup_filename}


@system_Router.get("/system/backups", response_model=List[str], tags=["system"])
async def list_backups(current_user: User = Depends(get_current_user)):
    """
    Lists all available backup files.
    """
    try:
        files = os.listdir(BACKUP_DIR)
        backup_files = sorted(
            [f for f in files if f.endswith(".dump")],
            reverse=True
        )
        return backup_files
    except FileNotFoundError:
        return []


@system_Router.post("/system/restore/{filename}", status_code=status.HTTP_202_ACCEPTED, tags=["system"])
async def restore_from_backup(
    filename: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Triggers a database restore task from a specific backup file.
    This is a DESTRUCTIVE operation and will overwrite the current database.
    """
    backup_filepath = os.path.join(BACKUP_DIR, filename)

    if not os.path.exists(backup_filepath):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup file not found.")

    db_settings = {
        "host": settings.POSTGRES_HOST,
        "port": settings.POSTGRES_PORT,
        "user": settings.POSTGRES_USER,
        "password": settings.POSTGRES_PASSWORD,
        "db": settings.POSTGRES_DB,
    }

    background_tasks.add_task(run_restore, db_settings, backup_filepath)

    return {"message": "Database restore process started from file.", "filename": filename}


@system_Router.delete("/system/backups/{filename}", status_code=status.HTTP_200_OK, tags=["system"])
async def delete_backup(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a specific backup file.
    """
    backup_filepath = os.path.join(BACKUP_DIR, filename)

    if not os.path.exists(backup_filepath):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup file not found.")
    
    if not filename.endswith(".dump"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type.")

    try:
        os.remove(backup_filepath)
        return {"message": "Backup file deleted successfully.", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete file: {e}")


@system_Router.get("/system/download-backup/{filename}", tags=["system"])
async def download_backup(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """
    Downloads a specific backup file.
    """
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename.")

    backup_filepath = os.path.join(BACKUP_DIR, filename)

    if not os.path.exists(backup_filepath):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup file not found.")

    return FileResponse(path=backup_filepath, media_type='application/octet-stream', filename=filename)
