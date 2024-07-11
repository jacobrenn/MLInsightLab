import sqlite3
import argon2
import string
import random
import os

DB_DIRECTORY = '/database'
DB_FILE = os.path.join(DB_DIRECTORY, 'permissions.db')

ADMIN_USERNAME = os.environ['ADMIN_USERNAME']
ADMIN_KEY = os.environ['ADMIN_KEY']

HASHED_ADMIN_KEY = argon2.PasswordHasher().hash(ADMIN_KEY)

# Function to generate an API key
def generate_api_key():
    """
    Generate an API key
    """
    key = ''.join(random.choices(string.ascii_letters + string.digits, k = 32))
    return f'odsp-{key}'

# Function to validate role
def validate_role(role):
    if role not in ['admin', 'data_scientist', 'user']:
        raise ValueError('Not a valid role')
    return True

# Set up the database
def setup_database():
    """
    Set up the database if it doesn't already exist

    NOTE: Can be run safely even if the database has already been created
    """

    # Create the users table if it does not already exist
    con = sqlite3.connect(DB_FILE)
    con.execute('CREATE TABLE IF NOT EXISTS users(username, role, key)')
    con.commit()
    con.close()

    # Add the admin user to users table if they do not already exist
    con = sqlite3.connect(DB_FILE)

    # Check whether the user already exists in the table
    res = con.execute(f'SELECT * FROM users WHERE username="{ADMIN_USERNAME}"')
    if len(res.fetchall()) == 0:
        con.execute(f'INSERT INTO users VALUES ("{ADMIN_USERNAME}", "admin", "{HASHED_ADMIN_KEY}")')
        con.commit()
    con.close()

    # Return True for completeness
    return True

# Validate user's key
def validate_user_key(username, key):
    """
    Validate a username, key combination

    If successful, returns the user's role

    If unsuccessful, raises an appropriate Exception
    """

    # Query the database for the user's information
    con = sqlite3.connect(DB_FILE)
    res = con.execute(f'SELECT * FROM users WHERE username="{username}"').fetchall()

    # If there is not record for the user in the database, then the user does not exist -> raise ValueError
    if len(res) == 0:
        raise ValueError('User does not exist')

    # If there is more than one record for the user in the database, then there are duplicate usernames -> raise ValueError
    if len(res) > 1:
        raise ValueError('Multiple user records exist')

    # Expand the username, role, and hashed key
    username, role, hashed_key = res[0]

    # Return the role of the user if the key is validated
    try:
        argon2.PasswordHasher().verify(hashed_key, key)
        return role
    except Exception as e:
        raise ValueError('Incorrect Key Provided')

# Create new user
def fcreate_user(username, role, api_key = None):
    """
    Create a new user with an assigned role and (optionally) with an API key

    If successful, returns the user's API key

    NOTE: If user with the specified username already exists, raises ValueError
    """

    # Establish connection to the database and check for the username already existing
    con = sqlite3.connect(DB_FILE)
    res = con.execute(f'SELECT * FROM users WHERE username="{username}"').fetchall()
    if len(res) > 0:
        raise ValueError('Username already exists')
    
    # If the API key is not already provided, generate the API key
    if api_key is None:
        api_key = generate_api_key()

    # Validate the prospective role
    validate_role(role)

    # Insert new user into the database
    con.execute(f'INSERT INTO users VALUES ("{username}", "{role}", "{api_key}")')
    con.commit()
    con.close()

    return api_key

# Delete a user
def fdelete_user(username):
    """
    Delete a user from the database
    """

    # Connect to the database
    con = sqlite3.connect(DB_FILE)
    con.execute(f'DELETE FROM users WHERE username="{username}"')
    con.commit()

    return True

# Issue a new API key for a user
def fissue_new_api_key(username, key = None):
    """
    Issue a new API key for a specified user

    NOTE: Raises ValueError if zero or more than one user exists with the username
    """

    # Connect to the database and ensure that the user already exists
    con = sqlite3.connect(DB_FILE)
    res = con.execute(f'SELECT * FROM users WHERE username="{username}"').fetchall()

    # Validate that only one user with that username exists
    if len(res) == 0:
        raise ValueError('User does not exist')
    elif len(res) > 1:
        raise ValueError('More than one user with that username exists')
    
    # Generate API key if one is not provided
    if key is None:
        key = generate_api_key()
    
    # Hash the key
    hashed_key = argon2.PasswordHasher().hash(key.encode('utf-8'))

    # Update user in the database
    con.execute(f'UPDATE users SET key="{hashed_key}" WHERE username="{username}"')
    con.commit()
    con.close()

    # Return the new API key
    return key

# Update a user's role
def fupdate_user_role(username, new_role):
    """
    Change a user's role
    """

    # Connect to the database and ensure that the user already exists
    con = sqlite3.connect(DB_FILE)
    res = con.execute(f'SELECT * FROM users WHERE username="{username}"').fetchall()

    # Validate that only one user with that username exists
    if len(res) == 0:
        raise ValueError('User does not exist')
    elif len(res) > 1:
        raise ValueError('More than one user with that username exists')
    
    # Validate the new role
    validate_role(new_role)

    # Update user role in the database
    con.execute(f'UPDATE users SET role="{new_role}" WHERE username="{username}"')
    con.commit()
    con.close()

    return new_role

# List all users
def flist_users():
    """
    List all of the users in the database
    """

    # Connect to the database
    con = sqlite3.connect(DB_FILE)
    res = con.execute('SELECT username, role FROM users').fetchall()
    con.close()
    return res
