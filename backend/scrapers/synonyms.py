# Define airport cities as a constant at the top of the file
AIRPORT_CITIES = [
    "München hbf",
    "Berlin hbf", 
    "Frankfurt hbf",
    "Düsseldorf hbf",
    "Stuttgart hbf",
    "Karlsruhe hbf"
]

league_priority = {
    "Bundesliga": 1,  
    "2.Bundesliga": 2, 
    "Champions League": 3,  
    "DFB-Pokal": 4,   
    "3.Liga": 5,
    "Europa League": 6,
    "Conference League": 7  
}

TEAM_SYNONYMS = {
    # Bundesliga 1
    "bayern": "Bayern Munich",
    "fc bayern münchen": "Bayern Munich",
    "bayern münchen": "Bayern Munich",
    "bayern munich": "Bayern Munich",
    "fcb": "Bayern Munich",
    "münchen": "Bayern Munich",
    "münchen bayern": "Bayern Munich",
    "münchen bayern munich": "Bayern Munich",
    "münchen fcb": "Bayern Munich",
    
    "bvb": "Borussia Dortmund",
    "dortmund": "Borussia Dortmund",
    "borussia dortmund": "Borussia Dortmund",
    "bvb 09": "Borussia Dortmund",
    "bvb09": "Borussia Dortmund",
    "bvb 09 dortmund": "Borussia Dortmund",
    "bvb09 dortmund": "Borussia Dortmund",
    "bvb 09 borussia dortmund": "Borussia Dortmund",
    "bvb09 borussia dortmund": "Borussia Dortmund",

    "leverkusen": "Bayer Leverkusen",
    "bayer 04 leverkusen": "Bayer Leverkusen",
    "bayer leverkusen": "Bayer Leverkusen",
    "bayer 04": "Bayer Leverkusen",
    "b04": "Bayer Leverkusen",
    "bayer 04 leverkusen": "Bayer Lever",
    "bayer leverkusen": "Bayer Leverkusen",

    "rbl": "RB Leipzig",
    "rb leipzig": "RB Leipzig",
    "leipzig": "RB Leipzig",

    "vfb stuttgart": "VfB Stuttgart",
    "stuttgart": "VfB Stuttgart",

    "sge": "Eintracht Frankfurt",
    "frankfurt": "Eintracht Frankfurt",
    "eintracht frankfurt": "Eintracht Frankfurt",

    "sc freiburg": "SC Freiburg",
    "freiburg": "SC Freiburg",

    "union berlin": "1. FC Union Berlin",
    "union": "1. FC Union Berlin",

    "tsg hoffenheim": "TSG Hoffenheim",
    "hoffenheim": "TSG Hoffenheim",

    "mainz": "1. FSV Mainz 05",
    "1. fsv mainz 05": "1. FSV Mainz 05",

    "wolfsburg": "VfL Wolfsburg",
    "vfl wolfsburg": "VfL Wolfsburg",

    "m'gladbach": "Borussia Mönchengladbach",
    "borussia mönchengladbach": "Borussia Mönchengladbach",

    "werder bremen": "Werder Bremen",
    "bremen": "Werder Bremen",

    "fc augsburg": "FC Augsburg",
    "augsburg": "FC Augsburg",

    "bochum": "VfL Bochum",
    "vfl bochum": "VfL Bochum",

    "1. fc heidenheim": "1. FC Heidenheim",
    "heidenheim": "1. FC Heidenheim",

    "fc st. pauli": "FC St. Pauli",
    "st. pauli": "FC St. Pauli",

    "holstein kiel": "Holstein Kiel",
    "kiel": "Holstein Kiel",

    # Bundesliga 2
    "1. fc köln": "1. FC Köln",
    "köln": "1. FC Köln",

    "sv darmstadt 98": "SV Darmstadt 98",
    "darmstadt": "SV Darmstadt 98",

    "fortuna düsseldorf": "Fortuna Düsseldorf",
    "düsseldorf": "Fortuna Düsseldorf",

    "hamburger sv": "Hamburger SV",
    "hsv": "Hamburger SV",
    "hamburg": "Hamburger SV",

    "karlsruher sc": "Karlsruher SC",
    "karlsruhe": "Karlsruher SC",

    "hannover 96": "Hannover 96",
    "hannover": "Hannover 96",

    "sc paderborn 07": "SC Paderborn 07",
    "paderborn": "SC Paderborn 07",

    "spvgg greuther fürth": "SpVgg Greuther Fürth",
    "fürth": "SpVgg Greuther Fürth",

    "hertha bsc": "Hertha BSC",
    "hertha": "Hertha BSC",

    "fc schalke 04": "FC Schalke 04",
    "schalke": "FC Schalke 04",

    "sv elversberg": "SV Elversberg",
    "elversberg": "SV Elversberg",

    "1. fc nürnberg": "1. FC Nürnberg",
    "nürnberg": "1. FC Nürnberg",

    "1. fc kaiserslautern": "1. FC Kaiserslautern",
    "k'lautern": "1. FC Kaiserslautern",
    "kaiserslautern": "1. FC Kaiserslautern",

    "1. fc magdeburg": "1. FC Magdeburg",
    "magdeburg": "1. FC Magdeburg",

    "eintracht braunschweig": "Eintracht Braunschweig",
    "braunschweig": "Eintracht Braunschweig",

    "ssv ulm 1846": "SSV Ulm 1846",
    "ulm": "SSV Ulm 1846",

    "preußen münster": "Preußen Münster",
    "münster": "Preußen Münster",

    "hansa rostock": "Hansa Rostock",
    "rostock": "Hansa Rostock",

    "regensburg": "SSV Jahn Regensburg",

    # 3. Liga
    "alemannia aachen": "Alemannia Aachen",
    "aachen": "Alemannia Aachen",

    "arminia bielefeld": "Arminia Bielefeld",
    "bielefeld": "Arminia Bielefeld",

    "borussia dortmund ii": "Borussia Dortmund II",
    "dortmund ii": "Borussia Dortmund II",

    "dynamo dresden": "Dynamo Dresden",
    "dresden": "Dynamo Dresden",

    "energie cottbus": "Energie Cottbus",
    "cottbus": "Energie Cottbus",

    "erzgebirge aue": "Erzgebirge Aue",
    "aue": "Erzgebirge Aue",

    "hannover 96 ii": "Hannover 96 II",
    "hannover ii": "Hannover 96 II",

    "fc ingolstadt 04": "FC Ingolstadt 04",
    "ingolstadt": "FC Ingolstadt 04",

    "tsv 1860 munich": "TSV 1860 Munich",
    "1860 münchen": "TSV 1860 Munich",

    "vfl osnabrück": "VfL Osnabrück",
    "osnabrück": "VfL Osnabrück",

    "rot-weiss essen": "Rot-Weiss Essen",
    "essen": "Rot-Weiss Essen",

    "fc saarbrücken": "FC Saarbrücken",
    "saarbrücken": "FC Saarbrücken",

    "sv sandhausen": "SV Sandhausen",
    "sandhausen": "SV Sandhausen",

    "spvgg unterhaching": "SpVgg Unterhaching",
    "unterhaching": "SpVgg Unterhaching",

    "vfb stuttgart ii": "VfB Stuttgart II",
    "vfb ii": "VfB Stuttgart II",

    "sc verl": "SC Verl",
    "verl": "SC Verl",

    "viktoria köln": "Viktoria Köln",
    "vikt. köln": "Viktoria Köln",

    "waldhof mannheim": "Waldhof Mannheim",
    "mannheim": "Waldhof Mannheim",
    "mannheim waldhof": "Waldhof Mannheim",

    "sv wehen wiesbaden": "SV Wehen Wiesbaden",
    "wiesbaden": "SV Wehen Wiesbaden",
    
    # New 3. Liga teams added
    "msv duisburg": "MSV Duisburg",
    "duisburg": "MSV Duisburg",
    "meidericher sv": "MSV Duisburg",
    "msv": "MSV Duisburg",
    
    "tsv havelse": "TSV Havelse",
    "havelse": "TSV Havelse",
    
    "tsg 1899 hoffenheim ii": "TSG Hoffenheim II",
    "tsg hoffenheim ii": "TSG Hoffenheim II",
    "hoffenheim ii": "TSG Hoffenheim II",
    "tsg ii": "TSG Hoffenheim II",
    "hoffenheim 2": "TSG Hoffenheim II",
    
    "1. fc schweinfurt 05": "1. FC Schweinfurt 05",
    "fc schweinfurt 05": "1. FC Schweinfurt 05",
    "schweinfurt 05": "1. FC Schweinfurt 05",
    "schweinfurt": "1. FC Schweinfurt 05",
    "fc schweinfurt": "1. FC Schweinfurt 05",

    "rostock": "Hansa Rostock",
    "fc hansa rostock": "Hansa Rostock",
    "hansa rostock": "Hansa Rostock"
}


# Bundesliga 1 teams, their stadiums, and Hauptbahnhof coordinates
bundesliga_1_stadiums = [
    {"team": "Bayern Munich", "stadium": "Allianz Arena", "stadium_location": [48.2188, 11.6247], "hbf": {"name": "München hbf", "location": [48.1402, 11.5586]}},
    {"team": "Borussia Dortmund", "stadium": "Signal Iduna Park", "stadium_location": [51.4926, 7.4519], "hbf": {"name": "Dortmund hbf", "location": [51.5175, 7.4593]}},
    {"team": "Bayer Leverkusen", "stadium": "BayArena", "stadium_location": [51.0382, 7.0023], "hbf": {"name": "Leverkusen Mitte", "location": [51.0340, 6.9826]}},
    {"team": "RB Leipzig", "stadium": "Red Bull Arena", "stadium_location": [51.3458, 12.3484], "hbf": {"name": "Leipzig hbf", "location": [51.3455, 12.3810]}},
    {"team": "VfB Stuttgart", "stadium": "Mercedes-Benz Arena", "stadium_location": [48.7922, 9.2320], "hbf": {"name": "Stuttgart hbf", "location": [48.7850, 9.1829]}},
    {"team": "Eintracht Frankfurt", "stadium": "Deutsche Bank Park", "stadium_location": [50.0685, 8.6454], "hbf": {"name": "Frankfurt hbf", "location": [50.1069, 8.6620]}},
    {"team": "SC Freiburg", "stadium": "Europa-Park Stadion", "stadium_location": [48.0203, 7.8306], "hbf": {"name": "Freiburg (Breisgau) hbf", "location": [47.9970, 7.8419]}},
    {"team": "1. FC Union Berlin", "stadium": "Stadion An der Alten Försterei", "stadium_location": [52.4574, 13.5681], "hbf": {"name": "Berlin hbf", "location": [52.5251, 13.3694]}},
    {"team": "TSG Hoffenheim", "stadium": "PreZero Arena", "stadium_location": [49.2382, 8.8889], "hbf": {"name": "Sinsheim (Elsenz) hbf", "location": [49.2528, 8.8787]}},
    {"team": "1. FSV Mainz 05", "stadium": "MEWA Arena", "stadium_location": [49.9841, 8.2242], "hbf": {"name": "Mainz hbf", "location": [49.9966, 8.2580]}},
    {"team": "VfL Wolfsburg", "stadium": "Volkswagen Arena", "stadium_location": [52.4334, 10.8037], "hbf": {"name": "Wolfsburg hbf", "location": [52.4296, 10.7870]}},
    {"team": "Borussia Mönchengladbach", "stadium": "BORUSSIA-PARK", "stadium_location": [51.1746, 6.3855], "hbf": {"name": "Mönchengladbach hbf", "location": [51.1960, 6.4413]}},
    {"team": "Werder Bremen", "stadium": "Weserstadion", "stadium_location": [53.0664, 8.8376], "hbf": {"name": "Bremen hbf", "location": [53.0833, 8.8136]}},
    {"team": "FC Augsburg", "stadium": "WWK Arena", "stadium_location": [48.3233, 10.8840], "hbf": {"name": "Augsburg hbf", "location": [48.3655, 10.8850]}},
    {"team": "1. FC Heidenheim", "stadium": "Voith-Arena", "stadium_location": [48.6826, 10.1616], "hbf": {"name": "Heidenheim hbf", "location": [48.6740, 10.1540]}},
    {"team": "FC St. Pauli", "stadium": "Millerntor-Stadion", "stadium_location": [53.5549, 9.9676], "hbf": {"name": "Hamburg hbf", "location": [53.5526, 10.0067]}},
    {"team": "1. FC Köln", "stadium": "RheinEnergieStadion", "stadium_location": [50.9335, 6.8750], "hbf": {"name": "Köln hbf", "location": [50.9423, 6.9583]}},
    {"team": "Hamburger SV", "stadium": "Volksparkstadion", "stadium_location": [53.5877, 9.8986], "hbf": {"name": "Hamburg hbf", "location": [53.5526, 10.0067]}}
]

# Bundesliga 2 teams, their stadiums, and Hauptbahnhof coordinates
bundesliga_2_stadiums = [
    {"team": "Arminia Bielefeld", "stadium": "Schüco-Arena", "stadium_location": [52.0296, 8.5164], "hbf": {"name": "Bielefeld hbf", "location": [52.0294, 8.5325]}},
    {"team": "VfL Bochum", "stadium": "Vonovia Ruhrstadion", "stadium_location": [51.4899, 7.2364], "hbf": {"name": "Bochum hbf", "location": [51.4786, 7.2245]}},
    {"team": "Holstein Kiel", "stadium": "Holstein-Stadion", "stadium_location": [54.3439, 10.1228], "hbf": {"name": "Kiel hbf", "location": [54.3140, 10.1319]}},
    {"team": "SV Darmstadt 98", "stadium": "Merck-Stadion am Böllenfalltor", "stadium_location": [49.8573, 8.6680], "hbf": {"name": "Darmstadt hbf", "location": [49.8728, 8.6298]}},
    {"team": "Fortuna Düsseldorf", "stadium": "Merkur Spiel-Arena", "stadium_location": [51.2612, 6.7333], "hbf": {"name": "Düsseldorf hbf", "location": [51.2190, 6.7949]}},
    {"team": "Karlsruher SC", "stadium": "Wildparkstadion", "stadium_location": [49.0246, 8.4293], "hbf": {"name": "Karlsruhe hbf", "location": [48.9939, 8.4006]}},
    {"team": "Hannover 96", "stadium": "HDI-Arena", "stadium_location": [52.3600, 9.7312], "hbf": {"name": "Hannover hbf", "location": [52.3779, 9.7415]}},
    {"team": "SC Paderborn 07", "stadium": "Benteler-Arena", "stadium_location": [51.7191, 8.7408], "hbf": {"name": "Paderborn hbf", "location": [51.7191, 8.7575]}},
    {"team": "SpVgg Greuther Fürth", "stadium": "Sportpark Ronhof Thomas Sommer", "stadium_location": [49.4936, 10.9986], "hbf": {"name": "Fürth hbf", "location": [49.4772, 10.9886]}},
    {"team": "Hertha BSC", "stadium": "Olympiastadion Berlin", "stadium_location": [52.5147, 13.2395], "hbf": {"name": "Berlin hbf", "location": [52.5249, 13.3694]}},
    {"team": "FC Schalke 04", "stadium": "Veltins-Arena", "stadium_location": [51.5548, 7.0676], "hbf": {"name": "Gelsenkirchen hbf", "location": [51.5175, 7.0850]}},
    {"team": "SV Elversberg", "stadium": "Ursapharm-Arena an der Kaiserlinde", "stadium_location": [49.3327, 7.1122], "hbf": {"name": "Neunkirchen hbf", "location": [49.3446, 7.1806]}},
    {"team": "1. FC Nürnberg", "stadium": "Max-Morlock-Stadion", "stadium_location": [49.4261, 11.1257], "hbf": {"name": "Nürnberg hbf", "location": [49.4456, 11.0820]}},
    {"team": "1. FC Kaiserslautern", "stadium": "Fritz-Walter-Stadion", "stadium_location": [49.4352, 7.7766], "hbf": {"name": "Kaiserslautern hbf", "location": [49.4403, 7.7498]}},
    {"team": "1. FC Magdeburg", "stadium": "MDCC-Arena", "stadium_location": [52.1204, 11.6714], "hbf": {"name": "Magdeburg hbf", "location": [52.1306, 11.6266]}},
    {"team": "Eintracht Braunschweig", "stadium": "Eintracht-Stadion", "stadium_location": [52.2846, 10.5550], "hbf": {"name": "Braunschweig hbf", "location": [52.2481, 10.5377]}},
    {"team": "Preußen Münster", "stadium": "Preußenstadion", "stadium_location": [51.9290, 7.6245], "hbf": {"name": "Münster (Westf) hbf", "location": [51.9565, 7.6346]}},
    {"team": "Dynamo Dresden", "stadium": "Rudolf-Harbig-Stadion", "stadium_location": [51.0358, 13.7461], "hbf": {"name": "Dresden hbf", "location": [51.0406, 13.7326]}}
]

third_liga_stadiums = [
    {"team": "SSV Ulm 1846", "stadium": "Donaustadion", "stadium_location": [48.4027, 10.0058], "hbf": {"name": "Ulm hbf", "location": [48.3984, 9.9916]}},
    {"team": "SSV Jahn Regensburg", "stadium": "Jahnstadion Regensburg", "stadium_location": [48.990856, 12.107238], "hbf": {"name": "Regensburg hbf", "location": [49.012222, 12.099444]}},
    {"team": "Alemannia Aachen", "stadium": "Tivoli", "stadium_location": [50.7910, 6.1059], "hbf": {"name": "Aachen hbf", "location": [50.7678, 6.0915]}},
    {"team": "Energie Cottbus", "stadium": "Stadion der Freundschaft", "stadium_location": [51.7453, 14.3564], "hbf": {"name": "Cottbus hbf", "location": [51.7457, 14.3343]}},
    {"team": "Erzgebirge Aue", "stadium": "Erzgebirgsstadion", "stadium_location": [50.5856, 12.7114], "hbf": {"name": "Aue (Sachs) Bahnhof", "location": [50.5861, 12.6956]}},
    {"team": "Hansa Rostock", "stadium": "Ostseestadion", "stadium_location": [54.0849, 12.0951], "hbf": {"name": "Rostock hbf", "location": [54.0755, 12.1327]}},
    {"team": "FC Ingolstadt 04", "stadium": "Audi Sportpark", "stadium_location": [48.7194, 11.4575], "hbf": {"name": "Ingolstadt hbf", "location": [48.7320, 11.4057]}},
    {"team": "TSV 1860 Munich", "stadium": "Grünwalder Stadion", "stadium_location": [48.1056, 11.5748], "hbf": {"name": "München hbf", "location": [48.1402, 11.5586]}},
    {"team": "VfL Osnabrück", "stadium": "Stadion an der Bremer Brücke", "stadium_location": [52.2785, 8.0681], "hbf": {"name": "Osnabrück hbf", "location": [52.2725, 8.0530]}},
    {"team": "Rot-Weiss Essen", "stadium": "Stadion an der Hafenstraße", "stadium_location": [51.4875, 6.9731], "hbf": {"name": "Essen hbf", "location": [51.4513, 7.0134]}},
    {"team": "FC Saarbrücken", "stadium": "Ludwigsparkstadion", "stadium_location": [49.2525, 6.9725], "hbf": {"name": "Saarbrücken hbf", "location": [49.2415, 6.9916]}},
    {"team": "VfB Stuttgart II", "stadium": "Gazi-Stadion auf der Waldau", "stadium_location": [48.7561, 9.1906], "hbf": {"name": "Stuttgart hbf", "location": [48.7850, 9.1829]}},
    {"team": "SC Verl", "stadium": "Sportclub Arena", "stadium_location": [51.8833, 8.5144], "hbf": {"name": "Gütersloh hbf", "location": [51.9069, 8.3785]}},
    {"team": "Viktoria Köln", "stadium": "Sportpark Höhenberg", "stadium_location": [50.9431, 7.0106], "hbf": {"name": "Köln hbf", "location": [50.9423, 6.9583]}},
    {"team": "Waldhof Mannheim", "stadium": "Carl-Benz-Stadion", "stadium_location": [49.4775, 8.5006], "hbf": {"name": "Mannheim hbf", "location": [49.4794, 8.4689]}},
    {"team": "SV Wehen Wiesbaden", "stadium": "BRITA-Arena", "stadium_location": [50.0736, 8.2386], "hbf": {"name": "Wiesbaden hbf", "location": [50.0717, 8.2433]}},
    #New teams added
    {"team": "TSG Hoffenheim II", "stadium": "Dietmar-Hopp-Stadion", "stadium_location": [49.2736322388, 8.8385966456], "hbf": {"name": "Sinsheim (Elsenz) hbf", "location": [49.2528, 8.8787]}},
    {"team": "MSV Duisburg", "stadium": "MSV-Arena", "stadium_location": [51.4054183783, 6.77386190454], "hbf": {"name": "Duisburg hbf", "location": [51.4292, 6.7750]}},
    {"team": "TSV Havelse", "stadium": "Wilhelm-Langrehr-Stadion", "stadium_location": [52.40887, 9.60198], "hbf": {"name": "Hannover hbf", "location": [52.3779, 9.7415]}},
    {"team": "1. FC Schweinfurt 05", "stadium": "Sachs-Stadion", "stadium_location": [50.05199, 10.20168], "hbf": {"name": "Schweinfurt hbf", "location": [50.0444, 10.2358]}}

]

# Add this new section after third_liga_stadiums
other_teams_stadiums = [
    {"team": "Borussia Dortmund II", "stadium": "Stadion Rote Erde", "stadium_location": [51.4925, 7.4519], "hbf": {"name": "Dortmund hbf", "location": [51.5175, 7.4593]}},
    {"team": "Hannover 96 II", "stadium": "Eilenriedestadion", "stadium_location": [52.3770, 9.7610], "hbf": {"name": "Hannover hbf", "location": [52.3779, 9.7415]}},
    {"team": "SV Sandhausen", "stadium": "Hardtwaldstadion", "stadium_location": [49.3525, 8.6461], "hbf": {"name": "Heidelberg hbf", "location": [49.4010, 8.6750]}},
    {"team": "SpVgg Unterhaching", "stadium": "Sportpark Unterhaching", "stadium_location": [48.0647, 11.6136], "hbf": {"name": "München hbf", "location": [48.1402, 11.5586]}}
]