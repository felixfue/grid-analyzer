# grid-analyzer

A simple implemented dashboard, that visualizes the bottlenecks in the US power grid based on Lawrence Berkeley National Laboratory (LBNL) interconnection queues "Queued-Up"-Dataset. 


Check out the dashboard on Streamlit-Community-Cloud:
*Link to Live-app on streamlit Community Cloud*

## git-clone

git clone https://github.com/felixfue/grid-analyzer.git
cd grid-analyzer


## env setup

This project uses a virtual environment (`venv`) to avoid version conflicts.
```bash 
python3 -m venv .venv 
# activate (macOS/Linux)
source .venv/bin/activate 
# activate (Windows PowerShell)
.venv\Scripts\Activate.ps1 
```
Make sure ur IDE uses this `.venv`as both the selected **interpreter** and the **jupyter kernel** for the notebooks.

## tech stack

**Frontend/Dashboard**: streamlit, plotly
**Backend**: Supabase/PostgreSQL
**EDA**: pandas, numPy, matplotlib, seaborn
**ETL**: pandas, sqlalchemy, psycopg2-binary

## dataset

[LBNL "Queued Up" Interconnection Queue Data](https://emp.lbl.gov/queues)
**Disclaimer**: Dataset must be downloaded manually and saved as *data/raw/LBNL_Queue_Data_25.xlsx* (exact file-name required!). Raw-data is excluded from version control via .gitignore and is therefore not included in this repo.

## setup

- check out ```notebooks/01_eda_lbnl.ipynb``` to get an overview of the dataset
	- dependencies:
		- pandas
		- numpy
		- matplotlib
		- seaborn
		- openpyxl
		- sqlalchemy
		- psycopg2-binary
		- ipykernel
- check out ```notebooks/02_etl_pipeline_supabase.ipynb``` to see how the data is loaded
	- to upload to your personal supabase-database u need to replace "[YOUR_PASSWORD]" in DB-URI with your own supabase-password

to start the dashboard u need to:
- make sure ur `.venv`is activated (see *env setup* abouve)
- place ur supabase-password local in ```.streamlit/secrets.toml``` 
	```DATABASE_URL = "postgresql://postgres.xxxxx:YOUR_PASSWORD@aws-0-eu-west-1.pooler.supabase.com:6543/postgres"```
- run ```pip install -r requirements.txt```
- run ```streamlit run app.py```

## deployment disclaimer

App is deployed via **Streamlit Community Cloud**.
Since `.streamlit/secrets.toml` is excluded from version control (see `.gitignore`), the `DATABASE_URL` secret is configured directly in the Streamlit Community Cloud dashboard under **App settings → Secrets**, using the same TOML format shown above. It is never committed to this repository. 

If you fork this project, u will need to set up ur own Supabase database (see ETL-notebook) and add ur own `DATABASE_URL`secret before deploying.

## license

This project is licensed under the MIT License.
Note: This license applies to the source code only. The LBNL "Queued Up" dataset is subject to its own terms of use – see the [data source](https://emp.lbl.gov/queues) for details.