import { useQuery, gql } from '@apollo/client';
import './App.css'

const GET_DASHBOARD = gql`
  query GetDashboard {
    salesReceipt(limit: 20) {
      name
      price_current
      price_label
      image_url
    }
    suggestedRecipes {
      title
      instructions
      estimated_cost
      image_url
      items {
        name
        price_current
      }
    }
  }
`;

function App() {
  const { loading, error, data } = useQuery(GET_DASHBOARD);

  if (loading) return <h1>👨‍🍳 Checking Inventory & Generating Menu...</h1>;
  if (error) return <h1 style={{color: 'red'}}>Error: {error.message}</h1>;

  return (
    <div style={{ maxWidth: "1000px", margin: "0 auto", padding: "2rem", fontFamily: "sans-serif", backgroundColor: "#f4f4f9", minHeight: "100vh" }}>
      
      {/* HEADER */}
      <div style={{ textAlign: "center", marginBottom: "3rem" }}>
        <h1 style={{ color: "#333" }}>GrocerySmart 🍎</h1>
        <p style={{ color: "#666" }}>AI-Generated Recipes based on Real-Time Sales</p>
      </div>

      {/* SECTION 1: THE RAW DATABASE (The Store) */}
      <div style={{ marginBottom: "3rem", backgroundColor: "white", padding: "1.5rem", borderRadius: "12px", boxShadow: "0 2px 5px rgba(0,0,0,0.05)" }}>
        <h3 style={{ borderBottom: "2px solid #eee", paddingBottom: "0.5rem", margin: "0 0 1rem 0" }}>🏭 Raw Store Inventory</h3>
        
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: "1rem" }}>
          {data.salesReceipt.map((item: any, i: number) => (
            <div key={i} style={{ border: "1px solid #f0f0f0", borderRadius: "8px", padding: "1rem", textAlign: "center", backgroundColor: "#fff" }}>
              <div style={{ fontSize: "0.9rem", fontWeight: "600", marginBottom: "0.5rem", height: "40px", overflow: "hidden" }}>{item.name}</div>
              <div style={{ color: "#2e7d32", fontWeight: "bold" }}>${item.price_current}</div>
            </div>
          ))}
        </div>
      </div>

      {/* SECTION 2: THE ALGORITHM (The Generated Recipes) */}
      <div>
        <h3 style={{ borderBottom: "2px solid #333", paddingBottom: "0.5rem", marginBottom: "1.5rem" }}>✨ AI Generated Menu</h3>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "2rem" }}>
          {data.suggestedRecipes.map((recipe: any, index: number) => (
            <div key={index} style={{ 
              border: "1px solid #e0e0e0", 
              borderRadius: "12px", 
              overflow: "hidden",
              boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
              backgroundColor: "white",
              display: "flex",
              flexDirection: "column"
            }}>
              {/* Card Header */}
              <div style={{ backgroundColor: "#2c3e50", color: "white", padding: "1rem" }}>
                <h3 style={{ margin: 0, fontSize: "1.1rem" }}>{recipe.title}</h3>
              </div>

              <div style={{ padding: "1.5rem", flex: 1 }}>
                
                {/* Cost Badge */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
                    <span style={{ fontSize: "0.85rem", color: "#888", textTransform: "uppercase", letterSpacing: "1px" }}>Total Cost</span>
                    <span style={{ fontSize: "1.4rem", fontWeight: "bold", color: "#27ae60" }}>${recipe.estimated_cost?.toFixed(2)}</span>
                </div>

                {/* INGREDIENTS LIST (Fixed Formatting) */}
                <div style={{ backgroundColor: "#f8f9fa", borderRadius: "8px", padding: "1rem", marginBottom: "1.5rem" }}>
                  <h4 style={{ margin: "0 0 0.5rem 0", fontSize: "0.9rem", color: "#555" }}>🛒 Ingredients (On Sale):</h4>
                  <ul style={{ padding: 0, margin: 0, listStyle: "none" }}>
                    {recipe.items.map((item: any, i: number) => (
                      <li key={i} style={{ 
                        display: "flex", 
                        justifyContent: "space-between", // Pushes text left and price right
                        borderBottom: i !== recipe.items.length -1 ? "1px dashed #e0e0e0" : "none", // Divider line
                        padding: "6px 0",
                        fontSize: "0.9rem"
                      }}>
                        <span style={{ color: "#333", marginRight: "10px" }}>{item.name}</span>
                        <span style={{ fontWeight: "bold", color: "#333" }}>${item.price_current}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Instructions */}
                <div>
                  <h4 style={{ margin: "0 0 0.5rem 0", fontSize: "0.9rem", color: "#555" }}>📝 Instructions:</h4>
                  <p style={{ fontSize: "0.9rem", color: "#666", lineHeight: "1.6", whiteSpace: "pre-line" }}>{recipe.instructions}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  )
}

export default App