
# Coal mines, energy transition, and political attitudes (East Germany)

 #distance calculations: EPSG:3035 (Europe / LAEA) which is appropriate for Germany-wide distance in meters.

from pathlib import Path

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf

ROOT = Path(".")
DATA_DIR = ROOT / "data"

BOUNDARIES_PATH = DATA_DIR / "boundaries" / "landkreise.shp"
ELECTIONS_PATH = DATA_DIR / "elections" / "btw2021_kreise.csv"
COAL_MINES_PATH = DATA_DIR / "coal mines" / "gem_coal_mines.csv"
SURVEY_PATH = DATA_DIR / "surveys" / "gem_coal_mines.csv"

# geographical boundaries
BOUNDARY_ID_COL = "id"           
BOUNDARY_NAME_COL = "name"        
BOUNDARY_STATE_COL = "bundesland" 

# electoral id to match with geographical data 
ELECT_ID_COL = "id" 
# share of afd voters              
ELECT_AFD_COL = "afd_share"       

# coal mine locations
COAL_LON_COL = "longitude"
COAL_LAT_COL = "latitude"
# operating or closed
COAL_STATUS_COL = "status"        
COAL_TYPE_COL = "coal_type"       

# excludes berlin (may include later with state FEs)
EAST_STATES = [
    "Brandenburg",
    "Sachsen",
    "Sachsen-Anhalt",
    "Thüringen",
    "Mecklenburg-Vorpommern",
]

DISTANCE_CRS = "EPSG:3035"
AFD_IS_PERCENT = True

## HELPERS

def assert_exists(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"{label} not found at: {path}\n"
            f"Update the path in CONFIG or place the file there."
        )

def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    return df


# load geographical boundaries

def load_boundaries() -> gpd.GeoDataFrame:
    assert_exists(BOUNDARIES_PATH, "Boundaries file")
    gdf = gpd.read_file(BOUNDARIES_PATH)
    gdf = standardize_columns(gdf)

    # subset to East Germany
    east = gdf[gdf[BOUNDARY_STATE_COL].isin(EAST_STATES)].copy()
    return east


# election results

def load_and_merge_elections(east: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    assert_exists(ELECTIONS_PATH, "Elections file")
    votes = pd.read_csv(ELECTIONS_PATH)
    votes = standardize_columns(votes)

    merged = east.merge(
        votes[[ELECT_ID_COL, ELECT_AFD_COL]],
        how="left",
        left_on=BOUNDARY_ID_COL,
        right_on=ELECT_ID_COL,
        validate="1:1",
    )

    # normalize afd share
    merged["afd_share"] = pd.to_numeric(merged[ELECT_AFD_COL], errors="coerce")
    if AFD_IS_PERCENT:
        merged["afd_share"] = merged["afd_share"] / 100.0

    return merged


# long and lat of coal mines

def load_coal_mines() -> gpd.GeoDataFrame:
    assert_exists(COAL_MINES_PATH, "Coal mines file")
    mines = pd.read_csv(COAL_MINES_PATH)
    mines = standardize_columns(mines)

    mines[COAL_LON_COL] = pd.to_numeric(mines[COAL_LON_COL], errors="coerce")
    mines[COAL_LAT_COL] = pd.to_numeric(mines[COAL_LAT_COL], errors="coerce")
    mines = mines.dropna(subset=[COAL_LON_COL, COAL_LAT_COL]).copy()

    mines_gdf = gpd.GeoDataFrame(
        mines,
        geometry=gpd.points_from_xy(mines[COAL_LON_COL], mines[COAL_LAT_COL]),
        crs="EPSG:4326",
    )
    return mines_gdf


# projections and distance to nearest mine

def add_distance_to_nearest_mine(east: gpd.GeoDataFrame, mines: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    east_m = east.to_crs(DISTANCE_CRS)
    mines_m = mines.to_crs(DISTANCE_CRS)

    # district centroids for nearest distance
    centroids = east_m.copy()
    centroids["centroid"] = centroids.geometry.centroid
    centroids = centroids.set_geometry("centroid")

    # nearest spatial join 
    nearest = gpd.sjoin_nearest(
        centroids,
        mines_m,
        how="left",
        distance_col="dist_to_mine_m",
    )

    east_m["dist_to_mine_km"] = nearest["dist_to_mine_m"] / 1000.0

    # return in original CRS (for mapping with basemaps, we may later reproject)
    east_out = east_m.to_crs(east.crs)
    return east_out


# visualize

def plot_basic_boundaries(east: gpd.GeoDataFrame, outpath: Path | None = None) -> None:
    ax = east.plot(edgecolor="black", facecolor="white", figsize=(8, 8))
    ax.set_title("East Germany District Boundaries")
    ax.set_axis_off()
    if outpath:
        plt.savefig(outpath, dpi=200, bbox_inches="tight")
    plt.show()

def plot_afd_choropleth(east: gpd.GeoDataFrame, outpath: Path | None = None) -> None:
    ax = east.plot(column="afd_share", legend=True, figsize=(8, 8), edgecolor="black")
    ax.set_title("AfD Vote Share (District Level)")
    ax.set_axis_off()
    if outpath:
        plt.savefig(outpath, dpi=200, bbox_inches="tight")
    plt.show()

def plot_mines_overlay(east: gpd.GeoDataFrame, mines: gpd.GeoDataFrame, outpath: Path | None = None) -> None:
    # mercator
    east_3857 = east.to_crs(3857)
    mines_3857 = mines.to_crs(3857)

    ax = east_3857.plot(edgecolor="black", facecolor="white", figsize=(8, 8))
    mines_3857.plot(ax=ax, markersize=10)

    ax.set_title("Coal Mine Locations (points) over East Germany Districts")
    ax.set_axis_off()

    if outpath:
        plt.savefig(outpath, dpi=200, bbox_inches="tight")
    plt.show()

def plot_distance_choropleth(east: gpd.GeoDataFrame, outpath: Path | None = None) -> None:
    ax = east.plot(column="dist_to_mine_km", legend=True, figsize=(8, 8), edgecolor="black")
    ax.set_title("Distance to Nearest Coal Mine (km)")
    ax.set_axis_off()
    if outpath:
        plt.savefig(outpath, dpi=200, bbox_inches="tight")
    plt.show()


# regs

def run_simple_regression(east: gpd.GeoDataFrame) -> None:
    df = east.dropna(subset=["afd_share", "dist_to_mine_km"]).copy()

    # ols only
    model = smf.ols("afd_share ~ dist_to_mine_km", data=df).fit(cov_type="HC1")
    print(model.summary())

# main processing

def main():

    out_dir = ROOT / "outputs"
    out_dir.mkdir(exist_ok=True)

    east = load_boundaries()
    plot_basic_boundaries(east, outpath=out_dir / "0east_boundaries.png")

    east = load_and_merge_elections(east)
    plot_afd_choropleth(east, outpath=out_dir / "0afd_share.png")

    mines = load_coal_mines()
    plot_mines_overlay(east, mines, outpath=out_dir / "mines_overlay.png")

    east = add_distance_to_nearest_mine(east, mines)
    plot_distance_choropleth(east, outpath=out_dir / "dist_to_mine.png")

    run_simple_regression(east)

    east.to_file(out_dir / "analysis.geojson", driver="GeoJSON")
    east.drop(columns="geometry").to_csv(out_dir / "analysis.csv", index=False)

if __name__ == "__main__":
    main()
