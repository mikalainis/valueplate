import React, { useState } from 'react';

const Preferences = ({ userId }) => {
  const [prefs, setPrefs] = useState({ vegan: false, keto: false });

  const savePreferences = async () => {
    const query = `
      mutation UpdatePrefs($userId: ID!, $vegan: Boolean, $keto: Boolean) {
        updatePreferences(userId: $userId, vegan: $vegan, keto: $keto)
      }
    `;

    const response = await fetch('http://localhost:8080/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        query, 
        variables: { userId, ...prefs } 
      }),
    });
    alert("Preferences Saved!");
  };

  return (
    <div className="p-4 bg-white rounded shadow">
      <h2 className="text-xl font-bold mb-4">Your Dietary Preferences</h2>
      <label className="block mb-2">
        <input type="checkbox" onChange={(e) => setPrefs({...prefs, vegan: e.target.checked})} /> Vegan
      </label>
      <label className="block mb-4">
        <input type="checkbox" onChange={(e) => setPrefs({...prefs, keto: e.target.checked})} /> Keto
      </label>
      <button onClick={savePreferences} className="bg-green-500 text-white p-2 rounded">Save</button>
    </div>
  );
};

export default Preferences;