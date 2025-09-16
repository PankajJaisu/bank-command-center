#!/bin/bash

echo "🔄 Updating database schema with new customer fields..."

# Try to connect to the database and run the SQL script
# You may need to adjust the connection parameters based on your database setup

# For SQLite (if using SQLite database)
if [ -f "ap_command_center.db" ]; then
    echo "📊 Using SQLite database..."
    sqlite3 ap_command_center.db < update_customer_schema.sql
    echo "✅ Database updated successfully!"
fi

# For PostgreSQL (if using PostgreSQL)
# Uncomment and adjust the following lines if using PostgreSQL:
# echo "📊 Using PostgreSQL database..."
# psql -d ap_command_center -f update_customer_schema.sql

# For MySQL (if using MySQL)
# Uncomment and adjust the following lines if using MySQL:
# echo "📊 Using MySQL database..."
# mysql -u username -p database_name < update_customer_schema.sql

echo "🚀 Database update completed!"
echo "💡 You can now test the dynamic data features in the application."

export GEMINI_API_KEY="AIzaSyD-9T2YTic364l5yhyBpYVxeIqfE4oNQP8"