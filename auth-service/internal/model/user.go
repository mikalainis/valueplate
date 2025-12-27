package models

import (
	"time"
	"github.com/google/uuid"
	"gorm.io/gorm"
)

type User struct {
	ID           string    `gorm:"primaryKey" json:"id"`
	Email        string    `gorm:"unique;not null" json:"email"`
	PasswordHash string    `gorm:"not null" json:"-"`
	ZipCode      string    `json:"zip_code"`
	PreferredStores []string `gorm:"type:text[]" json:"preferred_stores"`
	CreatedAt    time.Time `json:"created_at"`
}

// BeforeCreate hook to inject UUIDs
func (u *User) BeforeCreate(tx *gorm.DB) (err error) {
	u.ID = uuid.New().String()
	return
}