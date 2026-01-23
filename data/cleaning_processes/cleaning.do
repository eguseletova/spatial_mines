** coal mine tracker, preliminary data cleaning

* operational mines: current effects

** please import here the may 2025 v2 dataset from global coal mine tracker.
import excel using "~/spatial_mines/data/coal mines/Global-Coal-Mine-Tracker-May-2025-V2.xlsx", sh("GCMT Non-closed Mines") first clear

tab CountryArea
keep if CountryArea == "Germany"

gen east = .
replace east = 1 if StateProvince == "Saxony"
replace east = 1 if StateProvince == "Saxony-Anhalt"
replace east = 1 if StateProvince == "Brandenburg"
replace east = 1 if StateProvince == "Lusatia"


keep if east == 1

keep MineName CountryArea Owners MineType MiningMethod MineSizeKm2 WorkforceSize CoalType CoalGrade OpeningYear ClosingYear StateProvince Latitude Longitude CMMEmissionsCO2e20years 

destring WorkforceSize, replace

gen operational = 1

tempfile current
save `current'

** for the one closing in 2025: do an RDD? combine with previously closed mines. look into closed mines ("legacy effect" of mining in the region)

import excel using "~/spatial_mines/data/coal mines/Global-Coal-Mine-Tracker-May-2025-V2.xlsx", sh("GCMT Closed Mines") first clear

tab CountryArea
keep if CountryArea == "Germany"

gen east = .
replace east = 1 if StateProvince == "Brandenburg"
replace east = 1 if StateProvince == "Lusatia"
replace east = 1 if StateProvince == "Saxony"
replace east = 1 if StateProvince == "Saxony-Anhalt"

keep if east == 1

keep MineName CountryArea Owners MineType MiningMethod MineSizeKm2 WorkforceSize CoalType CoalGrade OpeningYear ReasonforClosure MineSiteStatus ClosingYear StateProvince Latitude Longitude 

destring Latitude, replace
destring Longitude, replace


// reason for closure: government order is most interesting.

gen operational = 0 

append using `current'

gen data_source = "Global Coal Mine Tracker May 2025 v2"

save "~/spatial_mines/data/coal mines/coal_mines.dta", replace
export delimited "~/spatial_mines/data/coal mines/coal_mines.csv", replace



