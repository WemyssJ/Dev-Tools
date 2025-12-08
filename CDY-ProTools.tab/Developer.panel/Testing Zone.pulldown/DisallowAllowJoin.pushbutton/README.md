# Disallow/Allow Joins

## Deskripsi

**Disallow/Allow Joins** adalah tool untuk mengontrol behavior join pada ujung-ujung structural framing elements (balok) dalam Revit. Tool ini memungkinkan user untuk disallow atau allow joins pada kedua ujung balok, yang berguna untuk mengontrol bagaimana balok terhubung satu sama lain dalam model struktur.

Tool ini sangat penting dalam structural modeling untuk memastikan koneksi balok yang benar dan menghindari masalah join yang tidak diinginkan dalam konstruksi.

## Fitur Utama

- **Dual Operation Mode**: Disallow atau Allow joins pada balok
- **Batch Processing**: Memproses multiple balok sekaligus
- **End-Specific Control**: Mengatur join behavior pada kedua ujung balok
- **Selection Filter**: Hanya memperbolehkan selection structural framing
- **Cross-Version Compatibility**: Mendukung multiple Revit API versions
- **Transaction Safety**: Semua perubahan dalam Revit transaction
- **Error Handling**: Comprehensive error handling dengan user feedback

## Cara Kerja

### Join Control Mechanism
1. **Element Selection**: User memilih structural framing elements
2. **Operation Choice**: Pilih Disallow atau Allow joins
3. **End Processing**: Mengatur join behavior pada end 0 dan end 1 setiap balok
4. **Batch Execution**: Memproses semua selected elements dalam satu transaction

### API Usage
```python
# Disallow joins pada kedua ujung
StructuralFramingUtils.DisallowJoinAtEnd(element, 0)  # End 0
StructuralFramingUtils.DisallowJoinAtEnd(element, 1)  # End 1

# Allow joins pada kedua ujung
StructuralFramingUtils.AllowJoinAtEnd(element, 0)    # End 0
StructuralFramingUtils.AllowJoinAtEnd(element, 1)    # End 1
```

## Langkah Penggunaan

### Basic Workflow
1. Jalankan script dari Modeling panel → Disallow/Allow Join
2. **Select Elements**: Pilih structural framing elements yang ingin dimodifikasi
3. **Choose Operation**: Pilih "Disallow Join" atau "Allow Join"
4. **Automatic Processing**: Script otomatis mengatur join behavior pada semua selected elements
5. **Result Notification**: Toast notification menampilkan summary hasil

### Selection Tips
- **Multiple Selection**: Gunakan Ctrl+click untuk memilih multiple balok
- **Filter Active**: Script hanya menerima structural framing elements
- **Cancel Option**: Klik ESC untuk cancel selection

## Persyaratan

### System Requirements
- **Revit**: 2020+
- **pyRevit**: Terinstall dan aktif
- **Structural Elements**: Project harus memiliki structural framing elements

### Project Requirements
- **Structural Framing**: Minimal satu structural framing element
- **Join Conditions**: Situasi dimana join control diperlukan
- **Selection Access**: User dapat select elements dalam model

## Join Behavior Control

### Disallow Join
- **Purpose**: Mencegah balok join secara otomatis pada ujung
- **Use Case**: Balok yang tidak boleh terhubung (structural separation)
- **Visual Effect**: Join symbol tidak muncul pada ujung balok
- **Construction Impact**: Balok diperlakukan sebagai elemen terpisah

### Allow Join
- **Purpose**: Mengizinkan balok join pada ujung (default behavior)
- **Use Case**: Balok yang perlu terhubung secara struktural
- **Visual Effect**: Join symbol muncul pada ujung balok
- **Construction Impact**: Balok diperlakukan sebagai satu sistem

## Tips Penggunaan

### Best Practices
- **Structural Intent**: Pastikan join behavior sesuai dengan structural design intent
- **Construction Logic**: Consider bagaimana balok akan dibangun di lapangan
- **Documentation**: Dokumentasi mengapa join di-disallow/allow
- **Team Communication**: Komunikasi dengan structural engineer

### Workflow Integration
- **Modeling Phase**: Control joins selama structural modeling
- **Coordination**: Pastikan join behavior sesuai dengan MEP coordination
- **Documentation**: Verify join conditions dalam structural drawings
- **Construction**: Ensure join behavior sesuai dengan construction methods

### Troubleshooting
- **No Effect**: Check apakah balok sudah physically connected
- **Selection Issues**: Pastikan memilih structural framing category
- **API Errors**: Update ke Revit version yang compatible
- **Transaction Failed**: Check model permissions dan worksharing status

## Teknologi

### Core Technologies
- **Revit API**: StructuralFramingUtils untuk join control
- **pyRevit**: Framework untuk UI dan transaction management
- **Selection API**: Filtered selection untuk structural elements

### Key Classes
- **StructuralFramingUtils**: Core API untuk join operations
- **ISelectionFilter**: Custom filter untuk structural framing
- **Transaction**: Safe database modifications

### Implementation Details
- **Cross-Version Support**: Compatible dengan Revit 2020-2026
- **Error Recovery**: Graceful handling dari API exceptions
- **Performance**: Efficient batch processing untuk large selections

## Integration dengan Tools Lain

### Complementary Tools
- **Join Elements Tools**: Manual join/unjoin operations
- **Structural Analysis**: Verification tools untuk structural integrity
- **Documentation Tools**: Drawing tools untuk join representation

### Workflow Position
- **Structural Modeling**: Control joins selama 3D modeling
- **Quality Assurance**: Verify join conditions sebelum analysis
- **Coordination**: Ensure proper joins untuk multi-discipline coordination

## Contoh Penggunaan

### Skenario: Cantilever Beam
```
Balok cantilever yang tidak boleh join dengan kolom:
1. Select cantilever beam
2. Choose "Disallow Join"
3. End 0 dan End 1 tidak akan join secara otomatis
4. Beam tetap sebagai elemen terpisah untuk deflection calculations
```

### Skenario: Continuous Beam System
```
Balok continuous yang perlu terhubung:
1. Select semua beams dalam continuous system
2. Choose "Allow Join"
3. Semua ends dapat join untuk structural continuity
4. System dihitung sebagai satu unit struktural
```

## Versi

- **Versi**: 1.0.0
- **Penulis**: Prasetyo
- **Tanggal**: 2024
- **Compatibility**: Revit 2020+
- **Dependencies**: Revit API, pyRevit

## Lisensi

Script ini adalah bagian dari PrasKaaPyKit extension untuk pyRevit, digunakan untuk keperluan internal dan profesional BIM workflow.

---

**PrasKaaPyKit - Modeling.panel/Disallow Allow Join**
*Professional Structural Join Control untuk BIM Modeling*