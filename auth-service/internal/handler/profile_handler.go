package handler

import (
	"grocerysmart/auth-service/internal/domain"
	"net/http"
	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type ProfileHandler struct {
	DB *gorm.DB
}

// UpdateProfile handles PUT /profile
func (h *ProfileHandler) UpdateProfile(c *gin.Context) {
	var req domain.UserProfile
	// Bind JSON to struct
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

    // Upsert logic (Insert or Update)
	result := h.DB.Save(&req)
	if result.Error != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update profile"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "Profile updated", "data": req})
}