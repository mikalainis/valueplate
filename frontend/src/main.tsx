import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// 1. We must import 'HttpLink' explicitly
import { ApolloClient, InMemoryCache, ApolloProvider, HttpLink } from '@apollo/client';

// 2. Create the connection link (The "Old Way" of just passing uri to client is what caused the error)
const link = new HttpLink({
  uri: 'https://8080-firebase-grocerysmart-1765111162305.cluster-vaxpk4ituncuosfn5e3k7xrloi.cloudworkstations.dev/query',
});

// 3. Initialize Client with that link
const client = new ApolloClient({
  link: link, // <--- Using the link here fixes the error
  cache: new InMemoryCache(),
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ApolloProvider client={client}>
      <App />
    </ApolloProvider>
  </StrictMode>,
)