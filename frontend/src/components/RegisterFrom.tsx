import React, { useState } from 'react';
import { useMutation, gql } from '@apollo/client';

const REGISTER_USER = gql`
  mutation Register($email: String!, $password: String!, $zip: String!) {
    register(email: $email, password: $password, zipCode: $zip) {
      token
      user {
        id
        email
      }
    }
  }
`;

export const RegisterForm: React.FC<{ zipCode: string }> = ({ zipCode }) => {
  const [form, setForm] = useState({ email: '', password: '' });
  const [register, { loading }] = useMutation(REGISTER_USER);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const { data } = await register({ variables: { ...form, zip: zipCode } });
      localStorage.setItem('token', data.register.token);
      window.location.href = '/dashboard';
    } catch (err) {
      console.error("Registration failed", err);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <input 
        type="email" 
        placeholder="Email" 
        className="p-2 border rounded"
        onChange={e => setForm({...form, email: e.target.value})}
      />
      <input 
        type="password" 
        placeholder="Password (min 8 chars)" 
        className="p-2 border rounded"
        onChange={e => setForm({...form, password: e.target.value})}
      />
      <button className="bg-berry text-white p-3 rounded-xl font-bold">
        {loading ? "Creating Account..." : "Join GrocerySmart"}
      </button>
    </form>
  );
};