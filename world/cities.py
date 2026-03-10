"""
Highway Hauler — US City and Interstate Highway Network.

50 cities connected by interstate highways with real approximate distances (miles).
Cities have attributes: state, region, population tier, and available services.
"""

# City data: key -> {name, state, region, tier, services}
# tier: 1=small, 2=medium, 3=large (affects contract volume)
# services: list of available services at this city
CITIES = {
    # Northeast
    "new_york": {"name": "New York", "state": "NY", "region": "northeast", "tier": 3, "desc": "The Big Apple. Massive freight hub at the mouth of the Hudson."},
    "boston": {"name": "Boston", "state": "MA", "region": "northeast", "tier": 2, "desc": "Historic port city. Lobster and electronics ship out daily."},
    "philadelphia": {"name": "Philadelphia", "state": "PA", "region": "northeast", "tier": 3, "desc": "City of Brotherly Love. Heavy industrial freight corridor."},
    "pittsburgh": {"name": "Pittsburgh", "state": "PA", "region": "northeast", "tier": 2, "desc": "Steel City. Where the rivers meet and the freight moves."},
    "buffalo": {"name": "Buffalo", "state": "NY", "region": "northeast", "tier": 1, "desc": "Gateway to Canada. Cold winters and hot wings."},

    # Southeast
    "atlanta": {"name": "Atlanta", "state": "GA", "region": "southeast", "tier": 3, "desc": "The crossroads of the South. Every highway leads through here."},
    "miami": {"name": "Miami", "state": "FL", "region": "southeast", "tier": 3, "desc": "End of the line — or the beginning. Citrus and cruise ship supplies."},
    "jacksonville": {"name": "Jacksonville", "state": "FL", "region": "southeast", "tier": 2, "desc": "Major port city on the St. Johns River."},
    "charlotte": {"name": "Charlotte", "state": "NC", "region": "southeast", "tier": 2, "desc": "Banking capital of the South. I-85 corridor hub."},
    "louisville": {"name": "Louisville", "state": "KY", "region": "southeast", "tier": 3, "desc": "UPS Worldport at SDF. The air freight capital of America."},
    "nashville": {"name": "Nashville", "state": "TN", "region": "southeast", "tier": 2, "desc": "Music City. Freight terminal by day, honky-tonks by night."},
    "birmingham": {"name": "Birmingham", "state": "AL", "region": "southeast", "tier": 2, "desc": "Steel City of the South. I-65 and I-20 crossroads."},
    "montgomery": {"name": "Montgomery", "state": "AL", "region": "southeast", "tier": 1, "desc": "Capital of Alabama. Civil rights history and I-65 corridor."},
    "mobile": {"name": "Mobile", "state": "AL", "region": "southeast", "tier": 2, "desc": "Gulf Coast port city. Where I-65 meets I-10."},
    "pensacola": {"name": "Pensacola", "state": "FL", "region": "southeast", "tier": 2, "desc": "Port of Pensacola off I-110. Naval base, Gulf shipping, and boating goods."},
    "tallahassee": {"name": "Tallahassee", "state": "FL", "region": "southeast", "tier": 1, "desc": "Florida's capital. I-10 corridor between the panhandle and Jacksonville."},
    "new_orleans": {"name": "New Orleans", "state": "LA", "region": "southeast", "tier": 2, "desc": "The Big Easy. Port of the Mississippi River."},
    "richmond": {"name": "Richmond", "state": "VA", "region": "southeast", "tier": 1, "desc": "Capital of Virginia. I-95 corridor rest stop."},

    # Midwest
    "chicago": {"name": "Chicago", "state": "IL", "region": "midwest", "tier": 3, "desc": "The Windy City. Largest freight rail hub in North America."},
    "detroit": {"name": "Detroit", "state": "MI", "region": "midwest", "tier": 2, "desc": "Motor City. Auto parts in, finished cars out."},
    "cleveland": {"name": "Cleveland", "state": "OH", "region": "midwest", "tier": 2, "desc": "Rock and Roll Capital. Great Lakes shipping meets I-90."},
    "columbus": {"name": "Columbus", "state": "OH", "region": "midwest", "tier": 2, "desc": "Dead center of Ohio. Distribution warehouse central."},
    "indianapolis": {"name": "Indianapolis", "state": "IN", "region": "midwest", "tier": 2, "desc": "Crossroads of America. Where I-65, I-69, I-70, and I-74 all meet."},
    "milwaukee": {"name": "Milwaukee", "state": "WI", "region": "midwest", "tier": 1, "desc": "Brew City. Beer and cheese head south on I-94."},
    "minneapolis": {"name": "Minneapolis", "state": "MN", "region": "midwest", "tier": 2, "desc": "Twin Cities. Northern gateway to the Great Plains."},
    "kansas_city": {"name": "Kansas City", "state": "MO", "region": "midwest", "tier": 2, "desc": "Heart of America. BBQ smoke and freight trains."},
    "st_louis": {"name": "St. Louis", "state": "MO", "region": "midwest", "tier": 2, "desc": "Gateway to the West. The Arch marks the dividing line."},
    "cincinnati": {"name": "Cincinnati", "state": "OH", "region": "midwest", "tier": 2, "desc": "Queen City on the Ohio River. Skyline chili and shipping."},

    # South Central
    "dallas": {"name": "Dallas", "state": "TX", "region": "south_central", "tier": 3, "desc": "Big D. Oil, cattle, and tech converge on the prairie."},
    "houston": {"name": "Houston", "state": "TX", "region": "south_central", "tier": 3, "desc": "Space City. Largest port in the Gulf. Petrochemical capital."},
    "san_antonio": {"name": "San Antonio", "state": "TX", "region": "south_central", "tier": 2, "desc": "Remember the Alamo. Military freight and border trade."},
    "oklahoma_city": {"name": "Oklahoma City", "state": "OK", "region": "south_central", "tier": 2, "desc": "OKC. Oil derricks and I-40 running straight through."},
    "memphis": {"name": "Memphis", "state": "TN", "region": "south_central", "tier": 2, "desc": "Home of FedEx. If it ships overnight, it came through here."},
    "little_rock": {"name": "Little Rock", "state": "AR", "region": "south_central", "tier": 1, "desc": "Capital of Arkansas. Quiet crossroads on I-40 and I-30."},

    # Mountain West
    "denver": {"name": "Denver", "state": "CO", "region": "mountain", "tier": 3, "desc": "Mile High City. Gateway to the Rockies. I-70 mountain passes ahead."},
    "salt_lake_city": {"name": "Salt Lake City", "state": "UT", "region": "mountain", "tier": 2, "desc": "Crossroads of the West. I-15 meets I-80 in the shadow of the Wasatch."},
    "albuquerque": {"name": "Albuquerque", "state": "NM", "region": "mountain", "tier": 1, "desc": "Route 66 town. Desert heat and long empty stretches ahead."},
    "el_paso": {"name": "El Paso", "state": "TX", "region": "mountain", "tier": 1, "desc": "Border town. Where Texas meets Mexico and New Mexico."},
    "billings": {"name": "Billings", "state": "MT", "region": "mountain", "tier": 1, "desc": "Montana's largest city. Wide open spaces and big sky country."},
    "boise": {"name": "Boise", "state": "ID", "region": "mountain", "tier": 1, "desc": "City of Trees. Potatoes ship out, tech workers ship in."},
    "cheyenne": {"name": "Cheyenne", "state": "WY", "region": "mountain", "tier": 1, "desc": "Capital of Wyoming. Wind and wide open I-80."},

    # Pacific West
    "los_angeles": {"name": "Los Angeles", "state": "CA", "region": "pacific", "tier": 3, "desc": "The Port of LA moves more freight than anywhere in America."},
    "san_francisco": {"name": "San Francisco", "state": "CA", "region": "pacific", "tier": 3, "desc": "The Bay. Tech cargo and Pacific Rim imports."},
    "san_diego": {"name": "San Diego", "state": "CA", "region": "pacific", "tier": 2, "desc": "America's Finest City. Border crossing and naval freight."},
    "portland": {"name": "Portland", "state": "OR", "region": "pacific", "tier": 2, "desc": "Rose City. Timber, craft beer, and Columbia River shipping."},
    "seattle": {"name": "Seattle", "state": "WA", "region": "pacific", "tier": 3, "desc": "Emerald City. Boeing, Amazon, and Pacific trade routes."},
    "sacramento": {"name": "Sacramento", "state": "CA", "region": "pacific", "tier": 2, "desc": "California's capital. Central Valley agriculture hub."},
    "las_vegas": {"name": "Las Vegas", "state": "NV", "region": "pacific", "tier": 2, "desc": "Sin City. What happens in Vegas ships out of Vegas."},
    "phoenix": {"name": "Phoenix", "state": "AZ", "region": "pacific", "tier": 3, "desc": "Valley of the Sun. Scorching heat and I-10 stretching to eternity."},
    "tucson": {"name": "Tucson", "state": "AZ", "region": "pacific", "tier": 1, "desc": "Old Pueblo. Desert outpost on the I-10 corridor."},

    # Great Plains
    "omaha": {"name": "Omaha", "state": "NE", "region": "plains", "tier": 2, "desc": "Gateway to the West. Beef processing capital of America."},
    "des_moines": {"name": "Des Moines", "state": "IA", "region": "plains", "tier": 1, "desc": "Heart of Iowa. Corn and insurance, as far as the eye can see."},
    "sioux_falls": {"name": "Sioux Falls", "state": "SD", "region": "plains", "tier": 1, "desc": "Largest city in South Dakota. I-90 and I-29 crossroads."},
    "wichita": {"name": "Wichita", "state": "KS", "region": "plains", "tier": 1, "desc": "Air Capital of the World. Aircraft manufacturing hub."},

    # Northwest
    "spokane": {"name": "Spokane", "state": "WA", "region": "northwest", "tier": 1, "desc": "Inland Empire hub. Where the forests meet the plains."},
}

# Highway connections: (city_a, city_b, distance_miles, highway_name)
# Real approximate interstate distances
HIGHWAYS = [
    # I-95 Corridor (East Coast: Boston to Miami)
    ("boston", "new_york", 215, "I-95"),
    ("new_york", "philadelphia", 97, "I-95"),
    ("philadelphia", "richmond", 290, "I-95"),
    ("richmond", "jacksonville", 560, "I-95"),
    ("jacksonville", "miami", 345, "I-95"),

    # I-85 Corridor (Richmond to Atlanta via Piedmont)
    ("richmond", "charlotte", 330, "I-85"),
    ("charlotte", "atlanta", 245, "I-85"),

    # I-90 Corridor (Northern: Boston to Seattle)
    ("boston", "buffalo", 450, "I-90"),
    ("buffalo", "cleveland", 190, "I-90"),
    ("cleveland", "chicago", 345, "I-90"),
    ("minneapolis", "sioux_falls", 230, "I-90"),
    ("sioux_falls", "billings", 620, "I-90"),
    ("billings", "spokane", 470, "I-90"),
    ("spokane", "seattle", 280, "I-90"),

    # I-94 Corridor (Detroit to Minneapolis)
    ("detroit", "chicago", 280, "I-94"),
    ("chicago", "milwaukee", 92, "I-94"),
    ("milwaukee", "minneapolis", 335, "I-94"),

    # I-80/I-76 Corridor (NYC to SF)
    ("new_york", "pittsburgh", 370, "I-80/I-76"),
    ("cheyenne", "salt_lake_city", 440, "I-80"),
    ("salt_lake_city", "sacramento", 585, "I-80"),
    ("sacramento", "san_francisco", 87, "I-80"),
    ("omaha", "des_moines", 140, "I-80"),
    ("omaha", "cheyenne", 490, "I-80"),

    # I-84 Corridor (SLC to Portland)
    ("salt_lake_city", "boise", 340, "I-84"),
    ("boise", "portland", 430, "I-84"),

    # I-70 Corridor (Pittsburgh to Denver)
    ("pittsburgh", "columbus", 185, "I-70"),
    ("columbus", "indianapolis", 175, "I-70"),
    ("indianapolis", "st_louis", 240, "I-70"),
    ("st_louis", "kansas_city", 250, "I-70"),
    ("kansas_city", "denver", 600, "I-70"),

    # I-10 Corridor (Jacksonville to LA — full east-west southern route)
    ("jacksonville", "tallahassee", 165, "I-10"),
    ("tallahassee", "pensacola", 195, "I-10"),
    ("pensacola", "mobile", 60, "I-10"),
    ("mobile", "new_orleans", 150, "I-10"),
    ("new_orleans", "houston", 350, "I-10"),
    ("houston", "san_antonio", 200, "I-10"),
    ("san_antonio", "el_paso", 550, "I-10"),
    ("el_paso", "tucson", 315, "I-10"),
    ("tucson", "phoenix", 115, "I-10"),
    ("phoenix", "los_angeles", 370, "I-10"),

    # I-75 Corridor (Detroit to Jacksonville)
    ("detroit", "cincinnati", 265, "I-75"),
    ("cincinnati", "atlanta", 460, "I-75"),
    ("atlanta", "jacksonville", 345, "I-75"),

    # I-65 Corridor (Chicago to Mobile)
    ("chicago", "indianapolis", 185, "I-65"),
    ("indianapolis", "louisville", 115, "I-65"),
    ("louisville", "nashville", 175, "I-65"),
    ("nashville", "birmingham", 190, "I-65"),
    ("birmingham", "montgomery", 90, "I-65"),
    ("montgomery", "mobile", 170, "I-65"),

    # I-71 Corridor (Cleveland to Louisville)
    ("cleveland", "columbus", 145, "I-71"),
    ("columbus", "cincinnati", 110, "I-71"),
    ("cincinnati", "louisville", 100, "I-71"),

    # I-64 Corridor (Richmond to St. Louis via Louisville)
    ("richmond", "louisville", 590, "I-64"),
    ("louisville", "st_louis", 265, "I-64"),

    # I-55 Corridor (Chicago to New Orleans)
    ("chicago", "st_louis", 300, "I-55"),
    ("st_louis", "memphis", 285, "I-55"),
    ("memphis", "new_orleans", 390, "I-55"),

    # I-35 Corridor (Minneapolis to San Antonio)
    ("minneapolis", "des_moines", 245, "I-35"),
    ("des_moines", "kansas_city", 195, "I-35"),
    ("kansas_city", "wichita", 200, "I-35"),
    ("wichita", "oklahoma_city", 160, "I-35"),
    ("oklahoma_city", "dallas", 205, "I-35"),
    ("dallas", "san_antonio", 275, "I-35"),

    # I-40 Corridor (Memphis to Albuquerque, then I-17 south to Phoenix)
    ("memphis", "little_rock", 135, "I-40"),
    ("little_rock", "oklahoma_city", 340, "I-40"),
    ("oklahoma_city", "albuquerque", 540, "I-40"),
    ("albuquerque", "phoenix", 450, "I-40/I-17"),
    ("memphis", "nashville", 210, "I-40"),

    # I-25 Corridor (El Paso to Denver)
    ("el_paso", "albuquerque", 265, "I-25"),
    ("albuquerque", "denver", 450, "I-25"),
    ("denver", "cheyenne", 100, "I-25"),

    # I-20 (Atlanta to Dallas via Birmingham)
    ("atlanta", "birmingham", 150, "I-20"),
    ("birmingham", "dallas", 630, "I-20"),

    # I-24/I-75 (Nashville to Atlanta via Chattanooga)
    ("nashville", "atlanta", 250, "I-24/I-75"),

    # I-15 Corridor (San Diego to Montana via Vegas/SLC)
    ("san_diego", "los_angeles", 120, "I-5/I-15"),
    ("los_angeles", "las_vegas", 270, "I-15"),
    ("las_vegas", "salt_lake_city", 420, "I-15"),

    # I-5 Corridor (West Coast: San Diego to Seattle)
    ("los_angeles", "sacramento", 385, "I-5"),
    ("sacramento", "portland", 580, "I-5"),
    ("portland", "seattle", 175, "I-5"),

    # Cross links
    ("cleveland", "pittsburgh", 130, "I-76"),
    ("buffalo", "pittsburgh", 220, "I-79"),
    ("dallas", "houston", 240, "I-45"),
    ("sioux_falls", "omaha", 175, "I-29"),
    ("omaha", "kansas_city", 185, "I-29"),
    ("phoenix", "las_vegas", 300, "US-93"),
]

# Cargo types with base values and weight
CARGO_TYPES = {
    "electronics": {"name": "Electronics", "base_pay_per_mile": 2.80, "weight": 8000, "desc": "Pallets of consumer electronics. Handle with care."},
    "produce": {"name": "Fresh Produce", "base_pay_per_mile": 3.20, "weight": 12000, "desc": "Perishable fruits and vegetables. Time-sensitive."},
    "auto_parts": {"name": "Auto Parts", "base_pay_per_mile": 2.20, "weight": 15000, "desc": "Engine blocks, transmissions, brake assemblies."},
    "furniture": {"name": "Furniture", "base_pay_per_mile": 2.00, "weight": 10000, "desc": "Sofas, tables, bedroom sets. Bulky but not heavy."},
    "lumber": {"name": "Lumber", "base_pay_per_mile": 1.80, "weight": 20000, "desc": "Construction lumber. Heavy and long."},
    "fuel": {"name": "Fuel (Hazmat)", "base_pay_per_mile": 3.50, "weight": 18000, "desc": "Gasoline and diesel. Hazmat cert required. Pays well."},
    "livestock": {"name": "Livestock", "base_pay_per_mile": 2.50, "weight": 16000, "desc": "Live cattle. Keep moving and don't brake hard."},
    "machinery": {"name": "Heavy Machinery", "base_pay_per_mile": 3.00, "weight": 25000, "desc": "Industrial equipment. Oversize load permits needed."},
    "clothing": {"name": "Clothing", "base_pay_per_mile": 2.40, "weight": 6000, "desc": "Retail clothing shipments. Light but valuable."},
    "medical": {"name": "Medical Supplies", "base_pay_per_mile": 3.80, "weight": 5000, "desc": "Pharmaceuticals and equipment. Priority freight."},
    "beer": {"name": "Beer & Beverages", "base_pay_per_mile": 2.10, "weight": 20000, "desc": "Cases of beer and soft drinks. Heavy liquid cargo."},
    "steel": {"name": "Steel", "base_pay_per_mile": 1.60, "weight": 30000, "desc": "Steel coils and beams. Maximum weight, minimum excitement."},
}

# Rest areas / truck stops along major highways
# These are NOT cities — they're intermediate stops for eating, sleeping, restrooms
REST_AREAS = [
    {"name": "Captain Travel Center", "highway": "I-65", "between": ("louisville", "nashville"), "mile": 80},
    {"name": "Heart's Travel Stop", "highway": "I-10", "between": ("pensacola", "mobile"), "mile": 30},
    {"name": "Soaring J Truck Stop", "highway": "I-40", "between": ("little_rock", "oklahoma_city"), "mile": 170},
    {"name": "Road America Travel Center", "highway": "I-95", "between": ("richmond", "jacksonville"), "mile": 280},
    {"name": "Nitro Stopping Center", "highway": "I-80", "between": ("omaha", "cheyenne"), "mile": 265},
    {"name": "Captain Soaring J", "highway": "I-70", "between": ("st_louis", "kansas_city"), "mile": 125},
    {"name": "Heart's Country Store", "highway": "I-35", "between": ("oklahoma_city", "dallas"), "mile": 100},
    {"name": "Road America Express", "highway": "I-75", "between": ("cincinnati", "atlanta"), "mile": 230},
    {"name": "Soaring J Plaza", "highway": "I-90", "between": ("sioux_falls", "billings"), "mile": 310},
    {"name": "Nitro Iron Skillet", "highway": "I-10", "between": ("houston", "san_antonio"), "mile": 100},
    {"name": "Captain Truck Stop", "highway": "I-55", "between": ("st_louis", "memphis"), "mile": 140},
    {"name": "Heart's Travel Stop", "highway": "I-5", "between": ("sacramento", "portland"), "mile": 290},
    {"name": "Road America Truck Stop", "highway": "I-20", "between": ("birmingham", "dallas"), "mile": 315},
    {"name": "Trapp Bros.", "highway": "I-80", "between": ("cheyenne", "salt_lake_city"), "mile": 220},
    {"name": "Big Tex Fuel Depot", "highway": "I-10", "between": ("new_orleans", "houston"), "mile": 175},
]


# Geography trivia questions
TRIVIA = [
    ("What state is known as the Sunshine State?", "florida"),
    ("The Gateway Arch is in which city?", "st louis"),
    ("What is the largest state by area?", "alaska"),
    ("Which state is known as the Lone Star State?", "texas"),
    ("Mount Rushmore is in which state?", "south dakota"),
    ("What city is known as the Windy City?", "chicago"),
    ("The Grand Canyon is in which state?", "arizona"),
    ("Which state is known as the Peach State?", "georgia"),
    ("What river forms most of the border between Iowa and Nebraska?", "missouri"),
    ("Yellowstone National Park is primarily in which state?", "wyoming"),
    ("What is the capital of California?", "sacramento"),
    ("Which Great Lake is entirely within the US?", "michigan"),
    ("What state is known as the Buckeye State?", "ohio"),
    ("The Alamo is in which Texas city?", "san antonio"),
    ("What is the smallest state by area?", "rhode island"),
    ("Which city is known as the Motor City?", "detroit"),
    ("Mount McKinley (Denali) is in which state?", "alaska"),
    ("What state is known as the Cornhusker State?", "nebraska"),
    ("The Liberty Bell is in which city?", "philadelphia"),
    ("What is the capital of Montana?", "helena"),
    ("Which state has the most coastline?", "alaska"),
    ("What city is known as the Big Easy?", "new orleans"),
    ("The Hoover Dam is near which city?", "las vegas"),
    ("What is the capital of Oregon?", "salem"),
    ("Which state is known as the Volunteer State?", "tennessee"),
]
