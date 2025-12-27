import React, { useState } from 'react';
import { useQuery, gql } from '@apollo/client';

const SEARCH_STORES = gql`
  query SearchStores($zip: String!, $radius: Int!) {
    searchStores(zipCode: $zip, radius: $radius) {
      id
      name
      address
      distance
    }
  }
`;

export const LocationPicker: React.FC = () => {
  const [zip, setZip] = useState("");
  const [selectedStores, setSelectedStores] = useState<string[]>([]);
  
  const { data, loading, refetch } = useQuery(SEARCH_STORES, {
    variables: { zip, radius: 10 },
    skip: zip.length < 5
  });

  return (
    <div className="p-6 max-w-md mx-auto bg-white rounded-xl shadow-md">
      <h2 className="text-xl font-bold text-teal-800 mb-4">Find Local Sales</h2>
      <input 
        type="text" 
        placeholder="Enter Zip Code"
        className="w-full p-2 border rounded mb-4"
        onChange={(e) => setZip(e.target.value)}
      />
      
      <div className="space-y-2">
        {data?.searchStores.map((store: any) => (
          <div key={store.id} className="flex items-center justify-between p-3 border rounded hover:bg-gray-50">
            <div>
              <p className="font-semibold">{store.name}</p>
              <p className="text-sm text-gray-500">{store.address}</p>
            </div>
            <input 
              type="checkbox" 
              onChange={() => setSelectedStores([...selectedStores, store.id])}
              className="h-5 w-5 accent-teal-600"
            />
          </div>
        ))}
      </div>
      
      <button 
        disabled={selectedStores.length === 0}
        className="mt-6 w-full bg-teal-600 text-white py-2 rounded-lg font-bold disabled:bg-gray-300"
      >
        Generate My Meal Plan
      </button>
    </div>
  );
};