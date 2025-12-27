package database

import (
    "database/sql"
    "fmt"
    "log"
    "os"
    "time"

    _ "github.com/lib/pq"
)

var DB *sql.DB

func InitDB() {
    connStr := fmt.Sprintf("host=%s user=%s password=%s dbname=%s sslmode=disable",
        os.Getenv("DB_HOST"),
        os.Getenv("DB_USER"),
        os.Getenv("DB_PASSWORD"),
        os.Getenv("DB_NAME"),
    )

    var err error
    for i := 0; i < 10; i++ {
        DB, err = sql.Open("postgres", connStr)
        if err == nil {
            err = DB.Ping()
        }
        if err == nil {
            log.Println("✅ [DATABASE] Connected successfully.")
            createTables() // Updated to plural
            return
        }
        log.Printf("⏳ [DATABASE] Waiting for Postgres... %v\n", err)
        time.Sleep(2 * time.Second)
    }
    log.Fatal("❌ [DATABASE] Could not connect to Postgres.")
}

func createTables() {
    // 1. Create Users
    userSchema := `
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        zip_code VARCHAR(10),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );`

    // 2. Create Preferences (Without the constraint for now)
    prefSchema := `
    CREATE TABLE IF NOT EXISTS user_preferences (
        user_id INTEGER PRIMARY KEY,
        preferred_store_ids TEXT[], 
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );`

    // 3. The Link (Separate step)
    linkSchema := `
    ALTER TABLE user_preferences 
    DROP CONSTRAINT IF EXISTS fk_user_link;
    
    ALTER TABLE user_preferences 
    ADD CONSTRAINT fk_user_link 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;`

    // Execute in order
    if _, err := DB.Exec(userSchema); err != nil {
        log.Println("❌ [DATABASE] Users table error:", err)
    }
    if _, err := DB.Exec(prefSchema); err != nil {
        log.Println("❌ [DATABASE] Preferences table error:", err)
    }
    
    // We wrap this in a check so it doesn't crash the whole app if it fails
    if _, err := DB.Exec(linkSchema); err != nil {
        log.Printf("⚠️ [DATABASE] Link failed (non-fatal): %v\n", err)
    } else {
        log.Println("✅ [DATABASE] Users and Preferences tables linked successfully.")
    }
}