package domain

import (
	"encoding/json"
	"time"
	"gorm.io/datatypes"
)

// FamilyMember represents one person in the household
type FamilyMember struct {
	Age           int     `json:"age" binding:"required"`
	Gender        string  `json:"gender" binding:"required,oneof=male female"`
	ActivityLevel string  `json:"activity_level" binding:"required,oneof=sedentary light moderate active"`
}

// UserProfile is the database model
type UserProfile struct {
	UserID             string         `gorm:"primaryKey;type:uuid" json:"user_id"`
	ZipCode            string         `json:"zip_code"`
	StorePreferences   datatypes.JSON `json:"store_preferences"` // Stored as array
	DietaryRestrictions datatypes.JSON `json:"dietary_restrictions"`
	
	// Storing complex struct slice as JSONB
	FamilyComposition  datatypes.JSON `json:"family_composition"` 
	
	WeeklyCalorieTarget int           `json:"weekly_calorie_target"`
	UpdatedAt          time.Time      `json:"updated_at"`
}