# MyNextHome

**MyNextHome** is an open-source real estate platform built using Django and GeoDjango. It helps users find rental and purchase properties with spatial search capabilities powered by PostgreSQL with PostGIS extension.

## Features

- 🏡 **Property Listings** - Users can list and browse properties.
- 📍 **Geolocation Support** - Spatial search with GeoDjango and PostGIS.
- 🗺️ **Interactive Maps** - Integrated maps for property locations.
- 🔍 **Advanced Search Filters** - Filter by price, location, property type, and amenities.
- 📢 **Real-time Notifications** - Get alerts for new listings.
- 📊 **Analytics Dashboard** - Insights into property demand and trends.
- 👥 **User Authentication** - Secure login and registration.

---

## Getting Started

### Prerequisites

Ensure you have the following installed:

- Python 3.8+
- Django 4.2+
- PostgreSQL 14+
- PostGIS extension
- Redis (for caching & real-time updates)
- Node.js (for frontend assets if applicable)

### Setting Up GeoDjango and PostgreSQL

#### **Linux (Ubuntu/Debian)**

##### 1. Install Required Packages

```sh
sudo apt update
sudo apt install binutils libproj-dev gdal-bin postgis postgresql-14-postgis-3
```

##### 2. Create a PostgreSQL Database with PostGIS Extension

```sh
sudo -u postgres psql
```

Inside PostgreSQL prompt, run:

```sql
CREATE DATABASE mynexthome;
CREATE USER mynexthome_user WITH PASSWORD 'your_password';
ALTER ROLE mynexthome_user SET client_encoding TO 'utf8';
ALTER ROLE mynexthome_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE mynexthome_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE mynexthome TO mynexthome_user;
\c mynexthome
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;
```

##### 3. Verify PostGIS Installation

```sh
psql -d mynexthome -c "SELECT postgis_version();"
```

#### **Windows**

##### 1. Install Required Packages

- Install [PostgreSQL](https://www.postgresql.org/download/windows/)
- During installation, select **PostGIS** extension.
- Install [GDAL](https://gdal.org/download.html) and add it to the system PATH.
- Install **Proj** from [OSGeo4W](https://trac.osgeo.org/osgeo4w/)

##### 2. Create a PostgreSQL Database with PostGIS Extension

Open **pgAdmin** or the **SQL Shell (psql)** and run:

```sql
CREATE DATABASE mynexthome;
CREATE USER mynexthome_user WITH PASSWORD 'your_password';
ALTER ROLE mynexthome_user SET client_encoding TO 'utf8';
ALTER ROLE mynexthome_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE mynexthome_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE mynexthome TO mynexthome_user;
\c mynexthome
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;
```

##### 3. Verify PostGIS Installation

```sql
SELECT postgis_version();
```

For more details, refer to:
- [GeoDjango Installation Guide](https://docs.djangoproject.com/en/stable/ref/contrib/gis/install/)
- [PostGIS Documentation](https://postgis.net/documentation/)

### Installation

#### 1. Clone the Repository

```sh
git clone https://github.com/yourusername/mynexthome.git
cd mynexthome
```

#### 2. Create a Virtual Environment

```sh
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

#### 3. Install Dependencies

```sh
pip install -r requirements.txt
```

#### 4. Configure Environment Variables

Create a `.env` file in the root directory and add the following:

```ini
DEBUG=True
SECRET_KEY=your_secret_key
DATABASE_URL=postgres://mynexthome_user:your_password@localhost:5432/mynexthome
REDIS_URL=redis://localhost:6379/0
```

#### 5. Set Up the Database

```sh
python manage.py makemigrations
python manage.py migrate
```

#### 6. Create a Superuser

```sh
python manage.py createsuperuser
```

#### 7. Run the Development Server

```sh
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` in your browser.

---

## Development

### Running Tests

```sh
pytest
```

### Running Celery Workers (if applicable)

```sh
celery -A mynexthome worker --loglevel=info
```

### Running Redis Server

```sh
redis-server
```

### Running Background Tasks

```sh
python manage.py process_tasks
```

---

## API Documentation

The API follows RESTful principles. You can access API documentation at:

```sh
http://127.0.0.1:8000/api/docs/
```

#### Example API Endpoints

- `GET /api/properties/` - List all properties
- `POST /api/properties/` - Create a new property listing
- `GET /api/properties/{id}/` - Retrieve a specific property

---

## Contributing

We welcome contributions! To contribute:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-name`).
3. Commit your changes (`git commit -m 'Add new feature'`).
4. Push to the branch (`git push origin feature-name`).
5. Open a Pull Request.

### Code Guidelines

- Follow **PEP 8** for Python code.
- Use **black** for formatting (`black .`).
- Write tests for new features.
- Document your code properly.

---

## License

This project is licensed under the **GNU General Public License v3.0**. See the [LICENSE](LICENSE) file for details.

---

## Contributors

Thanks to all contributors who make **MyNextHome** better! 🚀

---
## Sponsors 

MyNextHome is powered by Daraza and maintained by Arcticline Technologies

---
## Contact

For issues or suggestions, open a GitHub issue or reach out at:
📧 Email: [info@daraza.net](mailto:info@daraza.net])\
🌐 Website: [mynexthome.daraza.net](https://mynexthome.daraza.net)

