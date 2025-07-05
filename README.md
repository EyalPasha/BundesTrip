# BundesTrip

**Plan multi-city Bundesliga football trips with optimized train routes, live match data, and personalized itineraries.**

BundesTrip is a full-stack web application that helps users explore and plan custom football journeys across Germany. By combining real match schedules, train times, and smart optimization logic, users can generate travel plans that match their preferences — whether it's seeing the most matches or visiting the most cities.

---

## 🚀 Features

* 🧠 **Smart Trip Planning Algorithm**  
  Generates multi-day, multi-city itineraries with detailed optimization, showing the maximum possible trip routes and accommodation options. Whether you prefer fewer hotel changes and staying in one location or maximizing match attendance by traveling frequently, the algorithm provides highly personalized and logical travel plans tailored to your preferences.

* 🌐 **Responsive, Modern Frontend**  
  Enjoy a seamless experience on any device. The frontend is built with vanilla HTML, Bootstrap, and custom CSS for a clean, mobile-first design. Features include multi-step trip forms, animated loading states, and interactive components like Select2-powered dropdowns and visual league/team selectors. The UI adapts fluidly to phones, tablets, and desktops, ensuring intuitive navigation, touch-friendly controls, and accessibility enhancements throughout. All trip planning, filtering, and account management is handled via fast, fetch-based API calls for a smooth, app-like feel.

* 🔐 **Supabase Authentication**  
  Secure login and registration using Supabase Auth with JWT tokens. Sessions are managed on both frontend and backend, supporting persistent logins, password resets, and protected API endpoints.

* 💾 **Trip Saving & Retrieval**  
  Users can save favorite trips to their account and view them anytime. Saved trips include all itinerary details, match info, and preferences, allowing for easy re-planning or sharing.

* ⚽ **Live Bundesliga Fixture Data**  
  The app uses real, up-to-date Bundesliga (and other German leagues) match schedules, updating weekly.

* 🚄 **Integrated Train & Travel Data**  
  Combines football match times with real German train schedules to calculate feasible travel routes between cities.

* 🏨 **Hotel & Accommodation Optimization**  
  Suggests logical hotel changes to minimize unnecessary packing/unpacking, keeping users close to stadiums and city centers. The algorithm can prioritize fewer hotel changes or more match attendance, based on user choice.

* 🗺️ **Interactive Filtering & Sorting**  
  Powerful filters for teams, cities, dates, and leagues. Users can sort results by newest, favorites, most matches, or custom criteria. All filters update results instantly without page reloads.

* 📱 **Mobile-First & Accessibility**  
  Every page is optimized for mobile devices, with touch-friendly controls, large tap targets, and accessible navigation. ARIA labels, keyboard navigation, and high-contrast modes are supported for inclusivity.

* 🛠 **Admin Tools**  
  Includes endpoints for refreshing data, viewing logs, and system introspection. Admins can trigger fixture updates, monitor system health, and debug issues easily.

* 🔁 **Cancellation & Timeout Support**  
  Planning requests are cancellable by the user and automatically terminated after 120 seconds if still running, preventing server overload and improving UX.

* 📊 **User Stats & Dashboard**  
  Personalized dashboard displays trip history, favorites, and stats (e.g., total trips, matches attended). Users can manage their profile, update info, and view saved itineraries.

* 🔒 **Privacy & Security**  
  All sensitive data is protected with secure authentication, HTTPS, and best practices for user privacy. No personal data is shared or sold.

---

## 🧱 Tech Stack & Architecture

### Backend

* **Python 3.11+**
* **FastAPI** – High-performance API framework
* **Pydantic** – Request/response validation
* **Supabase** – PostgreSQL-based auth and storage
* **CSV-based Data** – Local static data for fixtures and train times
* **ThreadPoolExecutor** – Runs heavy CPU planning tasks asynchronously

### Frontend

* **HTML5 / CSS3 / JS**
* **Bootstrap** – UI framework
* **Select2** – Enhanced dropdowns
* **Supabase JS Client** – Auth management and data calls

### Configuration

Supabase credentials are injected at build time to avoid committing secrets.
Generate `frontend/services/supabase-config.js` by running:

```bash
$env:SUPABASE_URL="<your url>"; $env:SUPABASE_ANON_KEY="<your key>"; python scripts/generate_frontend_config.py
```

The generated file is gitignored and will be used by the frontend at runtime.

## 🧭 System Overview

1. **User Flow**:

   * Login via Supabase (frontend + backend JWT)
   * Submit a `/plan-trip` request with travel constraints
   * Backend runs async planning logic and returns grouped results
   * Save or retrieve trips via `/api/save-trip` or `/api/saved-trips`
   * Optionally cancel an ongoing request using `/cancel-trip/{request_id}`

2. **API Endpoints**:

   * `POST /plan-trip`
   * `POST /api/save-trip`
   * `GET /api/saved-trips`
   * `POST /cancel-trip/{request_id}`
   * `GET /request-status/{request_id}`
   * Admin endpoints: `/admin/refresh`, `/admin/logs`, etc.

---

## 🔍 How the Algorithm Works

The heart of BundesTrip is its **smart trip planning algorithm**:

* **Constraints-aware**: Generates trip itineraries based on the user's desired starting location, travel dates, and match preferences.
* **Real-time Optimization**: Combines match fixtures with precise train travel times for optimal routes.
* **Cancellation-aware**: Periodically checks for user-initiated cancellations or timeout (120s).
* **Performance-focused**: Optimized for efficiency even on complex, multi-city trips with heavy computation.

---

## 📸 Screenshots

<!-- First image alone -->
<p align="center">
  <img src="https://github.com/user-attachments/assets/9d7b9313-ec0b-4e2e-8383-7acc4e577e35" width="60%"/>
</p>

<!-- Next 3 images in one row -->
<table>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/ddf8583a-6bcc-4e6c-8430-30f8db5d03af" width="100%"/></td>
    <td><img src="https://github.com/user-attachments/assets/bab5f94c-c9c6-48b3-817d-4b9b77ded0c3" width="100%"/></td>
    <td><img src="https://github.com/user-attachments/assets/1a5625b6-9a54-4860-89c0-4b04508ffbef" width="100%"/></td>
  </tr>
</table>

<!-- Last 2 images in one row -->
<table>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/f9f80f5a-5699-4434-abbc-155ec5070a89" width="100%"/></td>
    <td><img src="https://github.com/user-attachments/assets/9fbfd1c0-3a97-4ea5-ae67-428683fd9d1c" width="100%"/></td>
  </tr>
</table>


---

## 📜 License

All content, code, and media in this repository — including screenshots, designs, and algorithms — are the intellectual property of the project author.

© 2025 Eyal Pasha. All rights reserved.

You may view and use this project for personal or educational purposes. Any reproduction, redistribution, or commercial use without explicit written permission is strictly prohibited.
