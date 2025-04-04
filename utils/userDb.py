import logging
import uuid
from werkzeug.security import check_password_hash, generate_password_hash
from config import Config
from datetime import datetime
from typing import Optional, List, Dict, Union

logging.basicConfig(level=logging.INFO)

async def fetch_user(user_id):
    if not user_id:
        return {"success": False, "message": "User ID is required"}
    
    select = 'email' if '@' in user_id and '.' in user_id else 'id'
    
    conn = await Config.get_db_connection()
    try:
        async with conn.cursor() as cursor:
            query = f"SELECT * FROM injustifyUsers WHERE {select} = %s"
            await cursor.execute(query, (user_id,))
            user = await cursor.fetchone()
            
            if user:
                userD = {
                    'success': True,
                    "id": user[1],
                    "email": user[0],
                    "name": user[2],
                    "picture": f"{Config.profilePath}/{user[3]}",
                    "verified_email": user[4],
                    "created_at": user[6].strftime('%Y-%m-%d %H:%M:%S'),
                }
                return {"success": True, "message": "User found", "user_info": userD}
            else:
                return {"success": False, "message": "User not found"}
    except Exception as err:
        logging.error("Error: %s", err)
        return {"success": False, "error": "An unexpected error occurred"}
    finally:
        if conn:
            Config.pool.release(conn)

async def validate_user_login(email, password):
    conn = await Config.get_db_connection()
    try:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT email, password FROM injustifyUsers WHERE email = %s", (email,))
            user = await cursor.fetchone()
            
            if user is None:
                return {"userFound": False}
            
            db_email, db_password = user
            if check_password_hash(db_password, password):
                user_info = await fetch_user(db_email)
                return {"user_info": user_info, "userFound": True, "truepassword": True}
            
            return {"user_info": None, "userFound": True, "truepassword": False}
    except Exception as err:
        logging.error("Error validating user login: %s", err)
        return {"error": "An error occurred during login validation"}
    finally:
        if conn:
            Config.pool.release(conn)


async def validate_user(user_email):
    try:
        conn = await Config.get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT verified_email FROM injustifyUsers WHERE email = %s",
                (user_email,)
            )
            user = await cursor.fetchone()
            
            return user is not None and user[0] == 1
    except Exception as err:
        logging.error("Error validating user: %s", err)
        return False
    finally:
        if conn:
            Config.pool.release(conn)  

async def create_new_user(Userinfo):
    if not Userinfo:
        return 'error'
    
    id = Userinfo.get('id', str(uuid.uuid4()))
    name = Userinfo['name']
    email = Userinfo['email']
    password = generate_password_hash(Userinfo.get('password', '')) if Userinfo.get('password') else None
    profilePicture = Userinfo.get('picture', 'nouser.jpeg')
    verified_email = Userinfo.get('verified_email', False)
    
    conn = await Config.get_db_connection()
    try:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO injustifyUsers (id, email, name, password, picture, verified_email) VALUES (%s, %s, %s, %s, %s, %s)",
                (id, email, name, password, profilePicture, verified_email)
            )
            await conn.commit()
            return 'success'
    except Exception as err:
        logging.error("Error: %s", err)
        return str(err)
    finally:
        if conn:
            Config.pool.release(conn)

async def update_user_password(username, password):
    if not username or not password:
        return {"success": False, "message": "Username and password are required"}
    
    password_hash = generate_password_hash(password)
    conn = await Config.get_db_connection()
    try:
        async with conn.cursor() as cursor:
            query = "UPDATE injustifyUsers SET password = %s WHERE email = %s"
            await cursor.execute(query, (password_hash, username))
            await conn.commit()
            affected_rows = cursor.rowcount
            
            if affected_rows == 0:
                return {"success": False, "message": "No user found with that email"}
            return {"success": True, "message": "Password updated successfully"}
    except Exception as db_err:
        logging.error("Database Error: %s", db_err)
        return {"success": False, "message": f"Database error: {str(db_err)}"}
    finally:
        if conn:
            Config.pool.release(conn)


async def fetch_downloads(
    user_id: Optional[int] = None,
    song_id: Optional[str] = None,
    name: Optional[str] = None,
    date: Optional[Union[str, datetime]] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    order_by: Optional[str] = None
) -> Optional[List[Dict]]:
    """
    Fetch downloads from the database with flexible filtering, sorting, and pagination.
    """
    conn = await Config.get_db_connection()
    try:
        async with conn.cursor() as cursor:
            query = "SELECT * FROM downloads WHERE 1=1"
            values = []

            if user_id:
                if '@' in user_id and '.' in user_id:
                    qr = "SELECT id FROM injustifyusers WHERE email = %s"
                    await cursor.execute(qr, (user_id,))
                    result = await cursor.fetchone()
                    if result:
                        user_id = result[0]

                query += " AND user_id = %s"
                values.append(user_id)
            
            if song_id:
                query += " AND song_id = %s"
                values.append(song_id)
            
            if name:
                query += " AND filename LIKE %s"
                values.append(f"%{name}%")
            
            if date:
                query += " AND DATE(timestamp) = %s"
                values.append(date)
            
            if order_by:
                query += f" ORDER BY {order_by}"
            
            if limit is not None:
                query += " LIMIT %s"
                values.append(limit)
            
            if offset is not None:
                query += " OFFSET %s"
                values.append(offset)

            await cursor.execute(query, values)
            results = await cursor.fetchall()

            downloads = [{
                'filesize': result[6],
                'filename': result[3],
                'thumbnail': result[14],
                'links': result[2],
                'timestamp': result[10].strftime('%Y-%m-%d %H:%M:%S'),
            } for result in results]
            
            return {"success": True, "downloads": downloads}
    
    except Exception as e:
        logging.error(f"Error fetching downloads: {e}")
        return {"success": False, "downloads": []}
    
    finally:
        if conn:
            Config.pool.release(conn)  # ✅ Release connection instead of closing
