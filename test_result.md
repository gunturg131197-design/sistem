#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  Perubahan pada EXCAVA.OPS:
  1. Nota Sparepart multi-item (nama, qty, harga satuan, total per item + total nota) + kolom HM service (kelipatan 250 jam).
  2. Semua nilai keuangan tampil format Rupiah (termasuk input live).
  3. Payroll: pilih unit, jam kerja auto dari Ops (HM akhir-awal), jam dibayar, sisa jam belum dibayar, tarif per jam; gaji = jam dibayar x tarif. 1 payroll = 1 unit.
  4. Laporan per unit (cars, operator, gaji, HM awal/akhir, total HM, sparepart) + download per unit & semua (PDF+Excel).

backend:
  - task: "Sparepart multi-item + hm_service"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "POST /spareparts sekarang menerima items[] (nama_sparepart, qty, harga_satuan) + hm_service. Backend hitung total per item & biaya total nota. GET tetum return items[]."
        -working: true
        -agent: "testing"
        -comment: "✅ TESTED & VERIFIED: POST /api/spareparts dengan items[] array berfungsi sempurna. Perhitungan total per item (qty*harga_satuan) benar: Item 1 (Filter Oli x2 @ Rp150k = Rp300k), Item 2 (Bucket Teeth x5 @ Rp200k = Rp1jt). Total biaya nota = Rp1.3jt. hm_service=250 tersimpan. nama_sparepart ringkasan berisi kedua nama item. GET /api/spareparts mengembalikan items[] lengkap."
  - task: "Payroll per-jam + unit + hours endpoint"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "PayrollCreate menerima unit_id, tarif_per_jam, jam_dibayar, kasbon. gaji=jam_dibayar*tarif. Endpoint baru GET /payroll/hours?operator_id=&unit_id= mengembalikan total_jam_kerja, total_jam_dibayar, jam_belum_dibayar (jam kerja dari operations HM akhir-awal)."
        -working: true
        -agent: "testing"
        -comment: "✅ TESTED & VERIFIED: GET /api/payroll/hours berfungsi sempurna. Sebelum pembayaran: total_jam_kerja=8.0 (dari operations HM 110-118), total_jam_dibayar=0, jam_belum_dibayar=8.0. POST /api/payroll dengan tarif_per_jam=50000, jam_dibayar=8, kasbon=100000 menghasilkan gaji=400000 (8*50000), gaji_bersih=300000 (400k-100k), jam_kerja snapshot=8.0, unit_label terisi. Setelah pembayaran: total_jam_dibayar=8.0, jam_belum_dibayar=0.0. Tracking jam kerja update dengan benar."
  - task: "Reports per unit endpoint"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "GET /reports/units mengembalikan rekap per unit: total_cars, hm_awal, hm_akhir, total_hm, total_gaji, total_kasbon, total_gaji_bersih, total_sparepart, operators[], serta detail operations/payroll/spareparts."
        -working: true
        -agent: "testing"
        -comment: "✅ TESTED & VERIFIED: GET /api/reports/units berfungsi sempurna. Agregasi data benar: total_cars=8 (5+3), hm_awal=100 (min), hm_akhir=118 (max), total_hm=18.0 (10+8), total_gaji=400000, total_gaji_bersih=300000, total_sparepart=1300000. Operators list berisi semua operator yang bekerja pada unit. RBAC berfungsi: operator hanya melihat unit miliknya."
  - task: "Automatic report numbering"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "POST /api/reports/number menerima {month, year} dan mengembalikan nomor laporan otomatis berformat LP/TTP/{seq}/{romawi bulan}/{tahun}. Counter berurutan dimulai dari 200."
        -working: true
        -agent: "testing"
        -comment: "✅ TESTED & VERIFIED: POST /api/reports/number berfungsi sempurna. Format nomor benar: LP/TTP/{seq}/{roman}/{year}. Seq dimulai dari 200 dan increment dengan benar (200→201). Roman numerals benar: VIII untuk bulan 8, III untuk bulan 3, XII untuk bulan 12. Counter persistent di MongoDB (app_counters collection)."
  - task: "Period filtering for reports"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "GET /api/reports/units?periode=YYYY-MM memfilter operations (tanggal), spareparts (tanggal), dan payroll (periode) sesuai periode yang diberikan. Tanpa parameter periode menampilkan semua data."
        -working: true
        -agent: "testing"
        -comment: "✅ TESTED & VERIFIED: GET /api/reports/units?periode=YYYY-MM berfungsi sempurna. Filter periode 2025-07 menampilkan data seed dengan benar: total_cars=5, total_hm=10, total_gaji=500000, total_gaji_bersih=400000, total_sparepart=1300000. Periode kosong (2025-06) menampilkan semua agregasi=0. Tanpa parameter periode menampilkan semua data (all-time >= filtered). Filter operations/spareparts by tanggal prefix, payroll by periode exact match."

frontend:
  - task: "Sparepart multi-item form + Rupiah"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/SparepartsPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Form nota dengan tombol Tambah Sparepart, qty, harga satuan (CurrencyInput), total per item & total nota; kolom HM service dengan hint kelipatan 250 jam."
  - task: "Payroll unit + jam + Rupiah"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/PayrollPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Pilihan unit, ringkasan jam kerja/dibayar/belum dibayar (fetch /payroll/hours), tarif per jam & kasbon CurrencyInput, preview gaji bersih."
  - task: "Reports page"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/ReportsPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Halaman /reports rekap per unit + download PDF/Excel per unit & semua unit. Nav 'Laporan' ditambahkan."

metadata:
  created_by: "main_agent"
  version: "1.2"
  test_sequence: 3
  run_ui: false

test_plan:
  current_focus: []
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    -agent: "main"
    -message: |
      Tolong test BACKEND saja. Login manual: POST /api/auth/login dengan admin/admin123 (admin) & budi/budi123 (operator) — cookie session_token dipakai untuk request berikutnya.
      Fokus test:
      1) POST /api/spareparts dengan payload {unit_id, nomor_nota, tanggal, hm_service, items:[{nama_sparepart,qty,harga_satuan}, ...]} → verifikasi tiap item.total = qty*harga_satuan & biaya = sum. GET /api/spareparts return items[].
      2) Buat unit (POST /api/units) & operation (POST /api/operations) sebagai admin agar ada jam kerja. Lalu GET /api/payroll/hours?operator_id=&unit_id= → cek total_jam_kerja sesuai (HM akhir-awal). POST /api/payroll {operator_id,unit_id,periode,tarif_per_jam,jam_dibayar,kasbon} → gaji=jam_dibayar*tarif, gaji_bersih=gaji-kasbon, jam_kerja snapshot terisi. Lalu GET /api/payroll/hours lagi → total_jam_dibayar bertambah, jam_belum_dibayar berkurang.
      3) GET /api/reports/units → cek agregasi (total_cars, hm_awal, hm_akhir, total_hm, total_gaji, total_sparepart) benar untuk unit yang punya data.
      4) RBAC: operator (budi) tidak bisa POST /api/spareparts & /api/payroll (harus 403).
    -agent: "testing"
    -message: |
      ✅ BACKEND TESTING COMPLETE - ALL TESTS PASSED (4/4)
      
      Tested all backend features with comprehensive test suite (/app/backend_test.py):
      
      1. ✅ SPAREPART MULTI-ITEM: POST /api/spareparts dengan items[] array berfungsi sempurna. Semua perhitungan benar (item.total = qty*harga_satuan, biaya total = sum items). hm_service tersimpan. GET /api/spareparts mengembalikan items[] lengkap.
      
      2. ✅ PAYROLL PER-JAM: GET /api/payroll/hours menghitung jam kerja dari operations dengan benar (total_jam_kerja, total_jam_dibayar, jam_belum_dibayar). POST /api/payroll menghitung gaji = jam_dibayar*tarif_per_jam, gaji_bersih = gaji-kasbon. jam_kerja snapshot tersimpan. Tracking jam update setelah pembayaran.
      
      3. ✅ REPORTS PER UNIT: GET /api/reports/units mengembalikan agregasi yang benar untuk semua field (total_cars, hm_awal/akhir, total_hm, total_gaji, total_gaji_bersih, total_sparepart, operators list).
      
      4. ✅ RBAC: Operator (budi) tidak bisa POST /api/spareparts & /api/payroll (403 Forbidden). Operator hanya melihat unit miliknya di reports.
      
      Semua backend API berfungsi dengan sempurna. Tidak ada bug atau masalah yang ditemukan.

    -agent: "main"
    -message: |
      RETEST BACKEND untuk 2 fitur baru pada laporan (login admin/admin123):
      1) POST /api/reports/number body {"month":8,"year":2026} → verifikasi field "nomor" berformat "LP/TTP/{seq}/VIII/2026", "seq" integer. Panggil 2x berturut → seq harus naik (mis. 200 lalu 201). Coba month lain (mis. 3) → romawi harus "III".
      2) GET /api/reports/units?periode=2025-07 → hanya menghitung operations/spareparts dengan tanggal berawalan 2025-07 & payroll periode 2025-07. Bandingkan dengan GET /api/reports/units tanpa periode (semua). Untuk periode yang tidak ada data (mis. 2020-01) → agregasi 0 untuk unit tsb.
      Data seed sudah ada: unit CAT 320D (unit_seed_01), ops tanggal 2025-07-02, payroll periode 2025-07, sparepart tanggal 2025-07-01. Jadi periode=2025-07 harus menampilkan angka, periode=2025-06 harus 0.
    -agent: "testing"
    -message: |
      ✅ BACKEND TESTING COMPLETE - ALL NEW FEATURES PASSED (2/2)
      
      Tested 2 new backend features for reports with comprehensive test suite (/app/backend_test_new_features.py):
      
      1. ✅ AUTOMATIC REPORT NUMBERING (POST /api/reports/number):
         - Format nomor benar: LP/TTP/{seq}/{roman}/{year}
         - Seq dimulai dari 200 dan increment dengan benar (200→201→202→203)
         - Roman numerals benar: VIII untuk bulan 8, III untuk bulan 3, XII untuk bulan 12
         - Counter persistent di MongoDB (app_counters collection)
         - Semua test cases passed: month 8/2026, sequential calls, month 3/2026, month 12/2025
      
      2. ✅ PERIOD FILTERING (GET /api/reports/units?periode=YYYY-MM):
         - Filter periode 2025-07 menampilkan data seed dengan benar:
           * total_cars=5 (expected 5) ✓
           * total_hm=10 (expected 10) ✓
           * total_gaji=500000 (expected 500000) ✓
           * total_gaji_bersih=400000 (expected 400000) ✓
           * total_sparepart=1300000 (expected 1300000) ✓
         - Periode kosong (2025-06) menampilkan semua agregasi=0 ✓
         - Tanpa parameter periode menampilkan semua data (all-time >= filtered) ✓
         - Filter logic benar: operations/spareparts by tanggal prefix, payroll by periode exact match
      
      Semua backend API untuk fitur baru berfungsi dengan sempurna. Tidak ada bug atau masalah yang ditemukan.
