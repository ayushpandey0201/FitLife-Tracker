import random

class FitnessTracker:
    def __init__(self, name, age, height, weight, target_weight, gender, is_vegetarian, weeks_to_target):
        self.name = name
        self.age = age
        self.height = height
        self.weight = weight
        self.target_weight = target_weight
        self.gender = gender
        self.is_vegetarian = is_vegetarian
        self.weeks_to_target = weeks_to_target
        self.bmi = self.calculate_bmi()
        self.daily_calorie_deficit = self.calculate_daily_calorie_deficit()
        self.calories_goal = self.calculate_calories_goal()
        self.exercise_plan = self.generate_exercise_plan()
        self.diet_plan = self.generate_diet_plan()

    def calculate_bmi(self):
        return self.weight / ((self.height / 100) ** 2)

    def calculate_daily_calorie_deficit(self):
        weight_change_needed = self.weight - self.target_weight
        total_calorie_deficit_needed = weight_change_needed * 7700  # Approx. 7700 calories per kg
        return total_calorie_deficit_needed / (self.weeks_to_target * 7)
    #source : https://www.medicinenet.com/how_to_calculate_calorie_deficit_for_weight_loss/article.htm
    
    def calculate_calories_goal(self):
        if self.gender == 'm':
            bmr = 10 * self.target_weight + 6.25 * self.height - 5 * self.age + 5
        elif self.gender == 'f':
            bmr = 10 * self.target_weight + 6.25 * self.height - 5 * self.age - 161
        daily_calories = bmr * 1.5
        return int(daily_calories - self.daily_calorie_deficit)
    #source : https://www.medicinenet.com/how_to_calculate_calorie_deficit_for_weight_loss/article.htm

    def generate_exercise_plan(self):
        exercises = ['Running', 'Cycling', 'Swimming', 'Yoga', 'Strength Training']
        return random.choice(exercises)

    def generate_diet_plan(self):
        # All the below data recommended by WHO
        if self.is_vegetarian:
            if self.bmi < 18.5:
                diet_options = {
                    'carbohydrates': random.randint(250, 350),
                    'proteins': random.randint(60, 120),
                    'fat': random.randint(30, 50),
                    'water': random.randint(2500, 3500)
                }
            elif 18.5 <= self.bmi < 25:
                diet_options = {
                    'carbohydrates': random.randint(200, 300),
                    'proteins': random.randint(50, 100),
                    'fat': random.randint(20, 40),
                    'water': random.randint(2000, 3000)
                }
            else:
                diet_options = {
                    'carbohydrates': random.randint(150, 250),
                    'proteins': random.randint(50, 80),
                    'fat': random.randint(20, 30),
                    'water': random.randint(2000, 3000)
                }
        else:
            if self.bmi < 18.5:
                diet_options = {
                    'carbohydrates': random.randint(250, 350),
                    'proteins': random.randint(80, 150),
                    'fat': random.randint(40, 60),
                    'water': random.randint(2500, 3500)
                }
            elif 18.5 <= self.bmi < 25:
                diet_options = {
                    'carbohydrates': random.randint(200, 300),
                    'proteins': random.randint(60, 120),
                    'fat': random.randint(30, 50),
                    'water': random.randint(2000, 3000)
                }
            else:
                diet_options = {
                    'carbohydrates': random.randint(150, 250),
                    'proteins': random.randint(60, 100),
                    'fat': random.randint(20, 40),
                    'water': random.randint(2000, 3000)
                }

        food_options = self.generate_food_options()
        diet_plan = {
            'diet_options': diet_options,
            'food_options': food_options
        }
        return diet_plan
    

    def generate_food_options(self):
        if self.is_vegetarian:
            food_options = {
                'morning': {
                    'Warm Water with Lime Juice': {
                        'carbs_per_100g': 5, 'proteins_per_100g': 0, 'fat_per_100g': 0,
                        'water_per_100g': 100, 'base_quantity': 100
                    },
                    'Coffee with low-fat milk': {
                        'carbs_per_100g': 10, 'proteins_per_100g': 5, 'fat_per_100g': 1,
                        'water_per_100g': 250, 'base_quantity': 100
                    },
                    'Poha': {
                        'carbs_per_100g': 23, 'proteins_per_100g': 2, 'fat_per_100g': 5,
                        'water_per_100g': 100, 'base_quantity': 100
                    },
                    'Upma': {
                        'carbs_per_100g': 30, 'proteins_per_100g': 4, 'fat_per_100g': 3,
                        'water_per_100g': 200, 'base_quantity': 100
                    },
                    '2 small Dosa': {
                        'carbs_per_100g': 50, 'proteins_per_100g': 6, 'fat_per_100g': 5,
                        'water_per_100g': 150, 'base_quantity': 100
                    },
                    'Fruit': {
                        'carbs_per_100g': 15, 'proteins_per_100g': 1, 'fat_per_100g': 0,
                        'water_per_100g': 85, 'base_quantity': 100
                    }
                },
                'afternoon': {
                    'Salad': {
                        'carbs_per_100g': 10, 'proteins_per_100g': 5, 'fat_per_100g': 2,
                        'water_per_100g': 200, 'base_quantity': 100
                    },
                    'Quinoa': {
                        'carbs_per_100g': 39, 'proteins_per_100g': 8, 'fat_per_100g': 3,
                        'water_per_100g': 180, 'base_quantity': 100
                    },
                    'Paneer Tikka': {
                        'carbs_per_100g': 5, 'proteins_per_100g': 15, 'fat_per_100g': 20,
                        'water_per_100g': 50, 'base_quantity': 100
                    },
                    'Dal with Rice': {
                        'carbs_per_100g': 38, 'proteins_per_100g': 9, 'fat_per_100g': 3,
                        'water_per_100g': 150, 'base_quantity': 100
                    }
                },
                'night': {
                    '2 Chapathi': {
                        'carbs_per_100g': 40, 'proteins_per_100g': 6, 'fat_per_100g': 3,
                        'water_per_100g': 100, 'base_quantity': 100
                    },
                    'Vegetable Stir Fry': {
                        'carbs_per_100g': 20, 'proteins_per_100g': 5, 'fat_per_100g': 2,
                        'water_per_100g': 100, 'base_quantity': 100
                    },
                    'Soup': {
                        'carbs_per_100g': 15, 'proteins_per_100g': 5, 'fat_per_100g': 1,
                        'water_per_100g': 250, 'base_quantity': 100
                    },
                    'Rajma Rice': {
                        'carbs_per_100g': 30, 'proteins_per_100g': 8, 'fat_per_100g': 3,
                        'water_per_100g': 150, 'base_quantity': 100
                    }
                }
            }
        else:
            food_options = {
                'morning': {
                    'Warm Water with Lime Juice': {
                        'carbs_per_100g': 5, 'proteins_per_100g': 0, 'fat_per_100g': 0,
                        'water_per_100g': 100, 'base_quantity': 100
                    },
                    'Coffee with low-fat milk': {
                        'carbs_per_100g': 10, 'proteins_per_100g': 5, 'fat_per_100g': 1,
                        'water_per_100g': 250, 'base_quantity': 100
                    },
                    'Oatmeal': {
                        'carbs_per_100g': 27, 'proteins_per_100g': 6, 'fat_per_100g': 4,
                        'water_per_100g': 150, 'base_quantity': 100
                    },
                    'Eggs': {
                        'carbs_per_100g': 1, 'proteins_per_100g': 6, 'fat_per_100g': 5,
                        'water_per_100g': 70, 'base_quantity': 100
                    },
                    'Fruit': {
                        'carbs_per_100g': 15, 'proteins_per_100g': 1, 'fat_per_100g': 0,
                        'water_per_100g': 85, 'base_quantity': 100
                    }
                },
                'afternoon': {
                    'Salad': {
                        'carbs_per_100g': 10, 'proteins_per_100g': 5, 'fat_per_100g': 2,
                        'water_per_100g': 200, 'base_quantity': 100
                    },
                    'Chicken Breast': {
                        'carbs_per_100g': 0, 'proteins_per_100g': 31, 'fat_per_100g': 4,
                        'water_per_100g': 100, 'base_quantity': 100
                    },
                    'Paneer Tikka': {
                        'carbs_per_100g': 5, 'proteins_per_100g': 15, 'fat_per_100g': 20,
                        'water_per_100g': 50, 'base_quantity': 100
                    },
                    'Dal with Rice': {
                        'carbs_per_100g': 38, 'proteins_per_100g': 9, 'fat_per_100g': 3,
                        'water_per_100g': 150, 'base_quantity': 100
                    },
                    'Fish Curry with Rice': {
                        'carbs_per_100g': 20, 'proteins_per_100g': 25, 'fat_per_100g': 10,
                        'water_per_100g': 150, 'base_quantity': 100
                    }
                },
                'night': {
                    '2 Chapathi': {
                        'carbs_per_100g': 40, 'proteins_per_100g': 6, 'fat_per_100g': 3,
                        'water_per_100g': 100, 'base_quantity': 100
                    },
                    'Chicken Grill': {
                        'carbs_per_100g': 0, 'proteins_per_100g': 25, 'fat_per_100g': 5,
                        'water_per_100g': 150, 'base_quantity': 100
                    },
                    'Soup': {
                        'carbs_per_100g': 15, 'proteins_per_100g': 5, 'fat_per_100g': 1,
                        'water_per_100g': 250, 'base_quantity': 100
                    },
                    'Pasta': {
                        'carbs_per_100g': 50, 'proteins_per_100g': 10, 'fat_per_100g': 2,
                        'water_per_100g': 200, 'base_quantity': 100
                    }
                }
            }

        return food_options
    
    def calculate_food_intake(self, meal_type):
        food_options = self.generate_food_options()
        chosen_food = random.choice(list(food_options[meal_type].keys()))
 
        # Determine suggested quantity based on weight goals
        if self.weight > self.target_weight:
            # Suggest lower quantity to help lose weight
            suggested_quantity = random.randint(50, 150)
        elif self.weight < self.target_weight:
            # Suggest higher quantity to help gain weight
            suggested_quantity = random.randint(150, 300)
        else:
            # Maintain current weight
            suggested_quantity = random.randint(100, 200)

        food_details = food_options[meal_type][chosen_food]

        food_intake = {
            'quantity': suggested_quantity,
            'carbs': (food_details['carbs_per_100g'] / food_details['base_quantity']) * suggested_quantity, 
            'proteins': (food_details['proteins_per_100g'] / food_details['base_quantity']) * suggested_quantity,
            'fat': (food_details['fat_per_100g'] / food_details['base_quantity']) * suggested_quantity,
            'water': (food_details['water_per_100g'] / food_details['base_quantity']) * suggested_quantity
            
        }

        return chosen_food, food_intake
        
#2---------------------------------------------------------------------------------------------------
print()

class UserDietTracker(FitnessTracker):
    def __init__(self, name,age,height,weight,target_weight,gender,preference,weeks_to_target):
        super().__init__(name,age,height,weight,target_weight,gender,preference,weeks_to_target)
        self.food_intake = {}

    def input_food_intake(self):
        meals = ['morning', 'afternoon', 'night']
        for meal in meals:
            print(f"\nAvailable options for {meal} meal:")
            options = self.diet_plan['food_options'][meal]
            index = 1
            for food in options:
                print(f"{index}.{food} (base quantity: {options[food]['base_quantity']}g)")
                index += 1

            choice = int(input(f"Select your {meal} meal by entering the corresponding number: ")) - 1
            food_item = list(options.keys())[choice]
            quantity = int(input(f"Enter the quantity (in grams) for {food_item}: "))
            self.food_intake[meal] = {
                'food_item': food_item,
                'quantity': quantity,
                'nutrients': self.calculate_nutrients(food_item, quantity, meal)
            }

    def calculate_nutrients(self, food_item, quantity, meal):
        food_data = self.diet_plan['food_options'][meal][food_item]
        base_quantity = food_data['base_quantity']
        multiplier = quantity / base_quantity
        nutrients = {
            'carbohydrates': food_data['carbs_per_100g'] * multiplier,
            'proteins': food_data['proteins_per_100g'] * multiplier,
            'fat': food_data['fat_per_100g'] * multiplier,
            'water': food_data['water_per_100g'] * multiplier
        }
        return nutrients

    def generate_feedback(self):
        total_nutrients = {
            'carbohydrates': 0,
            'proteins': 0,
            'fat': 0,
            'water': 0
        }

        for meal in self.food_intake:
            for nutrient in total_nutrients:
                total_nutrients[nutrient] += self.food_intake[meal]['nutrients'][nutrient]

        feedback = "Daily Nutrient Intake Summary:\n"
        feedback += f"Carbohydrates: {total_nutrients['carbohydrates']}g\n"
        feedback += f"Proteins: {total_nutrients['proteins']}g\n"
        feedback += f"Fat: {total_nutrients['fat']}g\n"
        feedback += f"Water: {total_nutrients['water']}ml\n"

        feedback += "\nFeedback:\n"
        return feedback

    def daily_feedback(self, calories_burned):
        total_carbs = sum(self.food_intake[meal]['nutrients']['carbohydrates'] for meal in self.food_intake)
        total_proteins = sum(self.food_intake[meal]['nutrients']['proteins'] for meal in self.food_intake)
        total_fat = sum(self.food_intake[meal]['nutrients']['fat'] for meal in self.food_intake)
        total_water = sum(self.food_intake[meal]['nutrients']['water'] for meal in self.food_intake)

        dfeedback = f"Today's Feedback for {self.name}:\n"
        dfeedback += f"Calories Goal: {self.calories_goal}, Calories Burned: {calories_burned}\n"
        dfeedback += f"Exercise Planned: {self.exercise_plan}\n"
        dfeedback += f"Diet Plan: {self.diet_plan['diet_options']}\n"
        dfeedback += f"Food Intake: Morning - {self.food_intake['morning']['food_item']} ({self.food_intake['morning']['quantity']}g), "
        dfeedback += f"Afternoon - {self.food_intake['afternoon']['food_item']} ({self.food_intake['afternoon']['quantity']}g), "
        dfeedback += f"Night - {self.food_intake['night']['food_item']} ({self.food_intake['night']['quantity']}g)\n"
        dfeedback += f"Total Intake: {total_carbs}g carbs, {total_proteins}g proteins, {total_fat}g fats, {total_water}ml water\n"

        if calories_burned >= self.calories_goal:
            dfeedback += "Excellent work on burning enough calories today!\n"
        else:
            dfeedback += "Consider more exercise to burn additional calories.\n"

        if total_carbs >= self.diet_plan['diet_options']['carbohydrates']:
            dfeedback += "Good job on meeting your carbohydrate-rich foods intake goal!\n"
        else:
            dfeedback += "Try to eat more carbs to meet your goal.\n"

        if total_proteins >= self.diet_plan['diet_options']['proteins']:
            dfeedback += "Great job on meeting your protein intake goal!\n"
        else:
            dfeedback += "Consider eating more protein-rich foods to meet your goal.\n"

        if total_fat >= self.diet_plan['diet_options']['fat']:
            dfeedback += "Great job on meeting your fats intake goal!\n"
        else:
            dfeedback += "Consider eating more fat-rich foods to meet your goal.\n"

        if total_water >= self.diet_plan['diet_options']['water']:
            dfeedback += "Well done on meeting your water intake goal!\n"
        else:
            dfeedback += "Drink more water to stay hydrated.\n"

        return dfeedback

#3 ------------------------------------------------------------------------------------------------

print("Do you need the diet chart or analysis of the diet of the day ?")
print("1. Diet Chart")
print("2. Analysis of the diet")
i=int(input("Enter your choice (1/2) : "))
name=input("Enter your name : ")
age=int(input("Enter your age : "))
height=int(input("Enter your height in cm : "))
weight=int(input("Enter your weight in kgs : "))
target_weight=int(input("Enter your target_weight : "))
gender=input("Enter your gender m/f : ")
print("Enter your preference")
preference=int(input("Type 1 for veg diet or Type 2 for non-veg included diet : "))
if preference==1:
    preference=True
elif preference==2:
    preference=False 
weeks_to_target=int(input("in how many weeks would you like to achive your target weight : "))

if i==1:
    user = FitnessTracker(name,age,height,weight,target_weight,gender,preference,weeks_to_target)
    food_intake_today = {
        'morning': user.calculate_food_intake('morning'),
        'afternoon': user.calculate_food_intake('afternoon'),
        'night': user.calculate_food_intake('night')
    }
    for i,j in food_intake_today.items():
        print(f'At {i} : {j}')
    print("Healthy food for wealthy mood :)")

else: 
    print("Lets do analysis of your day")
    cal_burn=int(input("How much calories did you burn today : "))
    tracker = UserDietTracker(name,age,height,weight,target_weight,gender,preference,weeks_to_target)
    tracker.input_food_intake()
    feedback = tracker.generate_feedback()
    print(feedback)
    print(tracker.daily_feedback(cal_burn))
    print("Fitness is not a destination it's a way of life enjoy it :D")