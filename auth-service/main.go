package main

import (
	"log"
	"net/http"
	"os"

	"grocerysmart/auth-service/database"
	"grocerysmart/auth-service/graph"
	// "grocerysmart/auth-service/graph/model"

	"github.com/99designs/gqlgen/graphql/handler"
	"github.com/99designs/gqlgen/graphql/playground"
)

const defaultPort = "8080"

// This function adds the headers that allow the Frontend to talk to us
func allowCors(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// 1. Allow any origin (Crucial for Cloud Workstations)
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "POST, GET, OPTIONS, PUT, DELETE")
		w.Header().Set("Access-Control-Allow-Headers", "Accept, Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization")

		// 2. Handle "Preflight" requests (Browser asking permission first)
		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		next.ServeHTTP(w, r)
	})
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = defaultPort
	}

	// Initialize Database
	database.InitDB()

	// Ensure the "Item" table exists so we don't crash
	database.DB.Exec(`CREATE TABLE IF NOT EXISTS items (
		id SERIAL PRIMARY KEY,
		sku TEXT,
		name TEXT,
		brand TEXT,
		price_current FLOAT,
		price_regular FLOAT,
		price_label TEXT,
		image_url TEXT,
		is_keto BOOLEAN,
		is_vegan BOOLEAN
	)`)

	srv := handler.NewDefaultServer(graph.NewExecutableSchema(graph.Config{Resolvers: &graph.Resolver{}}))

	http.Handle("/", playground.Handler("GraphQL playground", "/query"))
	
	// Wrap the query handler with our CORS function
	http.Handle("/query", allowCors(srv))

	log.Printf("connect to http://localhost:%s/ for GraphQL playground", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}