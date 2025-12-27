package database

import (
    "github.com/go-redis/redis/v8"
    "os"
    "context"
)

var RDB *redis.Client

func InitRedis() {
    RDB = redis.NewClient(&redis.Options{
        Addr: os.Getenv("REDIS_ADDR"), // This will be "redis:6379"
    })
    
    // Test connection
    ctx := context.Background()
    _, err := RDB.Ping(ctx).Result()
    if err != nil {
        panic("❌ [REDIS] Could not connect to Redis: " + err.Error())
    }
}