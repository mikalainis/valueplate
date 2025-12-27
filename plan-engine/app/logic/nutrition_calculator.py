from typing import List, Dict
from pydantic import BaseModel

class FamilyMember(BaseModel):
    age: int
    gender: str  # 'male' or 'female'
    activity_level: str  # 'sedentary', 'light', 'moderate', 'active'

class NutritionNeeds(BaseModel):
    total_weekly_calories: int
    daily_protein_grams: int
    daily_carbs_grams: int
    daily_fats_grams: int

class NutritionCalculator:
    """
    Calculates household nutritional needs using Harris-Benedict Equation.
    """

    ACTIVITY_MULTIPLIERS = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725
    }

    def calculate_bmr(self, member: FamilyMember) -> float:
        # Using average height/weight assumptions if not provided
        # Male: 175cm, 80kg | Female: 162cm, 68kg 
        # In a real V2, we would ask for specific weight/height.
        
        if member.gender.lower() == 'male':
            weight_kg = 80
            height_cm = 175
            # BMR = 88.362 + (13.397 x weight) + (4.799 x height) - (5.677 x age)
            return 88.362 + (13.397 * weight_kg) + (4.799 * height_cm) - (5.677 * member.age)
        else:
            weight_kg = 68
            height_cm = 162
            # BMR = 447.593 + (9.247 x weight) + (3.098 x height) - (4.330 x age)
            return 447.593 + (9.247 * weight_kg) + (3.098 * height_cm) - (4.330 * member.age)

    def calculate_household_needs(self, family_members: List[FamilyMember]) -> NutritionNeeds:
        total_daily_calories = 0

        for member in family_members:
            bmr = self.calculate_bmr(member)
            multiplier = self.ACTIVITY_MULTIPLIERS.get(member.activity_level, 1.2)
            total_daily_calories += (bmr * multiplier)

        # Standard Macro Split: 50% Carbs, 20% Protein, 30% Fat
        protein_cals = total_daily_calories * 0.20
        carbs_cals = total_daily_calories * 0.50
        fat_cals = total_daily_calories * 0.30

        return NutritionNeeds(
            total_weekly_calories=int(total_daily_calories * 7),
            daily_protein_grams=int(protein_cals / 4), # 4 cals per gram
            daily_carbs_grams=int(carbs_cals / 4),    # 4 cals per gram
            daily_fats_grams=int(fat_cals / 9)        # 9 cals per gram
        )