# Import necessary libraries
import streamlit as st
from streamlit_folium import folium_static
import folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable
import pandas as pd
import category_encoders as ce
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import mysql.connector


# Function to create Google Hybrid map
def create_google_map(location):
    m = folium.Map(location=location, zoom_start=6)
    folium.TileLayer(
        tiles='http://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
        attr='Google Hybrid',
        name='Google Hybrid',
        overlay=True
    ).add_to(m)
    return m


# Function to get coordinates from city and postal code
def get_coordinates(city, postal_code, country="GB"):  # Country code is optional, default is "GB" (United Kingdom)
    geolocator = Nominatim(user_agent="streamlit_app")
    try:
        # Try geocoding based on city
        location = geolocator.geocode(city + ", " + country)

        # If city geocoding fails, try geocoding based on postal code and country
        if not location:
            location = geolocator.geocode(postal_code + ", " + country)
    except GeocoderUnavailable as e:
        st.warning("Geocoding service is currently unavailable. Using default location.")
        location = None

    if location:
        return location.latitude, location.longitude
    else:
        return None, None

def connect_to_mysql():
    try:
        mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            password="studyjoel#123",
            database="sales_data_db"

        )
        return mydb

    except mysql.connector.Error as err:
        st.error(f"Error connecting to MySQL: {err}")


# Function to create database and table if they don't exist
def create_predicted_sales_table():
    try:
        # Connect to MySQL
        mydb = connect_to_mysql()
        mycursor = mydb.cursor()

        # Create database if it doesn't exist
        mycursor.execute("CREATE DATABASE IF NOT EXISTS sales_data_db")
        mycursor.execute("USE sales_data_db")

        # Create table if it doesn't exist
        create_table_query = """
        CREATE TABLE IF NOT EXISTS predicted_sales_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            city VARCHAR(255),
            postal_code VARCHAR(255),
            sub_category VARCHAR(255),
            product_name VARCHAR(255),
            quantity INT,
            discount FLOAT,
            year INT,
            month INT,
            predicted_sales DECIMAL(10, 2)
        )
        """
        mycursor.execute(create_table_query)

        mycursor.close()
        mydb.close()

    except mysql.connector.Error as err:
        st.error(f"Error creating database and table in MySQL: {err}")

# Function to store predicted sales in MySQL
def store_predicted_sales_in_mysql(selected_city, postal_code, selected_sub_category, product_name, quantity, discount, year, month, predicted_sales):
    try:
        # Connect to MySQL database
        mydb = connect_to_mysql()

        # Create cursor
        mycursor = mydb.cursor()

        # Insert predicted sales data into MySQL table
        insert_query = """
        INSERT INTO predicted_sales_data (city, postal_code, sub_category, product_name, quantity, discount, year, month, predicted_sales)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (selected_city, postal_code, selected_sub_category, product_name,
                  quantity, discount, year, month, predicted_sales)
        mycursor.execute(insert_query, values)

        # Commit changes and close cursor
        mydb.commit()
        mycursor.close()

        st.success("Predicted sales data stored in MySQL successfully!")

    except mysql.connector.Error as err:
        st.error(f"Error storing predicted sales data in MySQL: {err}")

    finally:
        # Close database connection
        if mydb.is_connected():
            mydb.close()
            st.write("MySQL connection closed.")




# Main Streamlit app
def main():
    st.title("Walmart Sales Prediction Dashboard")

    # Define dataset with cities and corresponding postal codes
    data = pd.read_csv('output.csv')
    

    # Place inputs in the sidebar
    with st.sidebar:
        st.text_input("Enter country code:", value="USA", key="country_code", disabled=True)

        # Select city from the available options
        cities = [" "] + sorted(set(data['City']))
        selected_city = st.selectbox("Select City:", cities)

        # Populate postal codes based on selected city
        postal_codes = [" "] + data[data['City'] == selected_city]['Postal Code'].unique().tolist()
        postal_code = st.selectbox("Select Postal Code:", postal_codes)

        # Select sub category from the available options
        subcategory = [" "] + sorted(set(data['Sub-Category']))
        selected_sub_category = st.selectbox("Select Sub-Category:", subcategory)

        # Populate product names based on selected sub category
        product_names = [" "] + data[data['Sub-Category'] == selected_sub_category]['Product Name'].unique().tolist()
        # Display product names in a dropdown input field
        product_name = st.selectbox("Select Product Name:", product_names)
        country = "USA"
        quantity = st.number_input("Enter Quantity:", min_value=1, step=1)
        discount = st.number_input("Enter Discount:", min_value=0.0, step=0.1)
        year = st.number_input("Enter Year:", min_value=2005, max_value=4000, step=1)
        month = st.number_input("Enter Month:", min_value=1, max_value=12, step=1)
        enter_button = st.button("Enter")

    # Check if the "Enter" button is clicked
    if enter_button:
        # Check if all fields are filled
        if selected_city != " " and postal_code != " " and selected_sub_category != " " and product_name != " " and year and month:
            # Get coordinates from city and postal code
            lat, lon = get_coordinates(selected_city, postal_code, country)

            if lat is not None and lon is not None:
                # Display the location on the map
                location = [lat, lon]
                m = create_google_map(location)

                # Model

                tar_encoders = ce.TargetEncoder()
                data['City'] = tar_encoders.fit_transform(data['City'], data['Sales'])
                encoded_city = tar_encoders.transform(pd.DataFrame({'City': [selected_city]}),
                                                      pd.DataFrame({'Sales': [0]}))
                encoded_city = encoded_city['City'].iloc[0]

                data['Sub-Category'] = tar_encoders.fit_transform(data['Sub-Category'], data['Sales'])
                encoded_subcategory = tar_encoders.transform(pd.DataFrame({'Sub-Category': [selected_sub_category]}),
                                                             pd.DataFrame({'Sales': [0]}))
                encoded_subcategory = encoded_subcategory['Sub-Category'].iloc[0]

                data['Product Name'] = tar_encoders.fit_transform(data['Product Name'], data['Sales'])
                encoded_productname = tar_encoders.transform(pd.DataFrame({'Product Name': [product_name]}),
                                                             pd.DataFrame({'Sales': [0]}))
                encoded_productname = encoded_productname['Product Name'].iloc[0]

                X = data.drop(['Sales'], axis=1)
                Y = data['Sales']

                ### test train split
                X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2, random_state=101)
                scaler = StandardScaler()
                X_train_std = scaler.fit_transform(X_train)
                X_test_std = scaler.transform(X_test)

                # random Forest
                rf = RandomForestRegressor(n_estimators=1000,
                                           max_depth=15)  # n_estimators = Number of trees in the forest
                rf.fit(X_train_std, Y_train)
                Y_pred_rf = rf.predict(X_test_std)

                user_input = pd.DataFrame({'City': [encoded_city], 'Postal Code': [postal_code],
                                           'Sub-Category': [encoded_subcategory], 'Product Name': [encoded_productname],
                                           'Quantity': [quantity], 'Discount': [discount], 'Year': [year],
                                           'Month': [month]})

                # Standardize user input
                user_input_std = scaler.transform(user_input)

                # Predicting Sales
                predicted_sales = rf.predict(user_input_std)



                # Add a marker with popup and tooltip for the provided location
                popup_text = f"""
                \u2022 City: {selected_city}
                \u2022 Postal Code: {postal_code}
                \u2022 Sub-Category: {selected_sub_category}
                \u2022 Product Name: {product_name}
                \u2022 Quantity: {quantity}
                \u2022 Discount: {discount}
                \u2022 Year: {year}
                \u2022 Month: {month}
                \u2022 predicted sales: {predicted_sales}
                """
                tooltip_text = f"""City: {selected_city}, Year: {year}, Month: {month}, Predicted sales: {predicted_sales[0]}"""
                folium.Marker(location, popup=folium.Popup(popup_text, parse_html=True), tooltip=tooltip_text,
                              permanent=True).add_to(m)

                folium_static(m)
                # Create predicted sales table if it doesn't exist
                create_predicted_sales_table()

                # Store predicted sales data in MySQL
                store_predicted_sales_in_mysql(selected_city, postal_code, selected_sub_category, product_name,
                                               quantity, discount, year, month, predicted_sales[0])
            else:
                st.write("Invalid location or location not found.")
        else:
            st.write("Please fill information.")


if __name__ == "__main__":
    main()
