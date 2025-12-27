package utils

import (
	"crypto/tls"
	"fmt"
	"net/smtp"
	"os"
)

func SendWeeklyEmail(toEmail string, body string) error {
	host := os.Getenv("SMTP_HOST")
	port := os.Getenv("SMTP_PORT")
	user := os.Getenv("SMTP_USER")
	pass := os.Getenv("SMTP_PASS")
	from := os.Getenv("FROM_EMAIL")

	subject := "Subject: Your Weekly GrocerySmart Plan 🛒\n"
	mime := "MIME-version: 1.0;\nContent-Type: text/html; charset=\"UTF-8\";\n\n"
	message := []byte(subject + mime + body)

	// Gmail Configuration
	auth := smtp.PlainAuth("", user, pass, host)
	tlsconfig := &tls.Config{
		InsecureSkipVerify: false,
		ServerName:         host,
	}

	// Connect to the server
	conn, err := smtp.Dial(host + ":" + port)
	if err != nil {
		return err
	}

	// Upgrade to TLS
	if err = conn.StartTLS(tlsconfig); err != nil {
		return err
	}

	// Auth and Send
	if err = conn.Auth(auth); err != nil {
		return err
	}

	if err = conn.Mail(from); err != nil {
		return err
	}

	if err = conn.Rcpt(toEmail); err != nil {
		return err
	}

	w, err := conn.Data()
	if err != nil {
		return err
	}

	_, err = w.Write(message)
	if err != nil {
		return err
	}

	err = w.Close()
	if err != nil {
		return err
	}

	return conn.Quit()
}