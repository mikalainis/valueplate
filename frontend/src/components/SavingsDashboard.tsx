import React from 'react';
import { useQuery, gql } from '@apollo/client';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const GET_OPTIMIZED_PLAN = gql`
  query GetOptimizedPlan($members: [FamilyMemberInput!]!, $storeIds: [String!]!) {
    generatePlan(members: $members, storeIds: $storeIds) {
      nutritionalTargets {
        totalWeeklyCalories
        dailyProteinGrams
        dailyCarbsGrams
        dailyFatsGrams
      }
      suggestedPlan {
        name
        cost
        regularCost
        calContribution
      }
    }
  }
`;

export const SavingsDashboard: React.FC<{ members: any[], storeIds: string[] }> = ({ members, storeIds }) => {
  const { data, loading, error } = useQuery(GET_OPTIMIZED_PLAN, {
    variables: { members, storeIds },
  });

  if (loading) return <div className="animate-pulse text-teal-600">Calculating your optimal savings...</div>;
  if (error) return <div className="text-berry">Error loading plan. Please check your store selection.</div>;

  const plan = data.generatePlan.suggestedPlan;
  const totalCost = plan.reduce((sum: number, item: any) => sum + item.cost, 0);
  const totalRegular = plan.reduce((sum: number, item: any) => sum + item.regularCost, 0);
  const savings = totalRegular - totalCost;

  return (
    <div className="bg-white p-6 rounded-3xl shadow-xl border border-gray-100">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h2 className="text-3xl font-extrabold text-gray-900">Your Weekly Plan</h2>
          <p className="text-gray-500 font-medium">Based on {members.length} family members</p>
        </div>
        <div className="text-right">
          <span className="block text-sm font-bold text-teal-600 uppercase tracking-wider">Total Savings</span>
          <span className="text-4xl font-black text-berry">${savings.toFixed(2)}</span>
        </div>
      </div>

      {/* Macro Breakdown */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-teal-50 p-4 rounded-2xl">
          <span className="block text-xs font-bold text-teal-700 uppercase">Protein</span>
          <span className="text-xl font-bold">{data.generatePlan.nutritionalTargets.dailyProteinGrams}g</span>
        </div>
        <div className="bg-orange-50 p-4 rounded-2xl">
          <span className="block text-xs font-bold text-orange-700 uppercase">Carbs</span>
          <span className="text-xl font-bold">{data.generatePlan.nutritionalTargets.dailyCarbsGrams}g</span>
        </div>
        <div className="bg-purple-50 p-4 rounded-2xl">
          <span className="block text-xs font-bold text-purple-700 uppercase">Fats</span>
          <span className="text-xl font-bold">{data.generatePlan.nutritionalTargets.dailyFatsGrams}g</span>
        </div>
      </div>

      {/* Cost Visualization */}
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={plan}>
            <XAxis dataKey="name" hide />
            <YAxis />
            <Tooltip />
            <Bar dataKey="cost" fill="#008080" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <button className="w-full mt-6 bg-teal-600 hover:bg-teal-700 text-white font-bold py-4 rounded-2xl transition-all">
        Export Shopping List to PDF
      </button>
    </div>
  );
};