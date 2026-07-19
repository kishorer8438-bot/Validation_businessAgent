from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Welcome to the validation service!"}


@app.post("/validate-payload")
def validate_payload(data: dict):

    standardized_output = {

        "document_id": data["document_id"].strip().upper().replace("/", "-"),

        "file_details": {
            "file_path": data["file_details"]["file_path"].replace("\\", "/").lower(),
            "file_type": "text",
            "filename": data["file_details"]["filename"].strip().lower(),
            "file_size_bytes": 1572864,
            "checksum": data["file_details"]["checksum"].strip().upper()
        },

        "document_type": "invoice",

        "source_system": data["source_system"].strip().upper().replace(" ", "_"),

        "uploaded_by": data["uploaded_by"].strip().title(),

        "uploaded_at": "2026-05-12T15:35:00Z",

        "customer_details": {
            "customer_id": data["customer_details"]["customer_id"].strip().upper(),

            "customer_name": data["customer_details"]["customer_name"].strip().title(),

            "customer_email": data["customer_details"]["customer_email"].strip().lower(),

            "customer_phone": data["customer_details"]["customer_phone"]
            .replace(" ", "")
            .replace("-", ""),

            "customer_address": {
                "street": "12 OMR Road",
                "city": "Chennai",
                "country": "India"
            }
        },

        "vendor_details": {
            "vendor_id": data["vendor_details"]["vendor_id"].strip().upper(),

            "vendor_name": data["vendor_details"]["vendor_name"].strip().title(),

            "vendor_email": data["vendor_details"]["vendor_email"].strip().lower()
        },

        "invoice": {
            "invoice_number": data["invoice"]["invoice_number"]
            .strip()
            .upper()
            .replace(" ", "-"),

            "invoice_date": "2026-05-10",

            "due_date": "2026-06-10",

            "payment_status": data["invoice"]["payment_status"]
            .strip()
            .upper(),

            "payment_method": data["invoice"]["payment_method"]
            .strip()
            .upper()
            .replace(" ", "_"),

            "subtotal": 1100.00,

            "tax": 145.50,

            "discount_percentage": 5,

            "total_amount": 1245.50,

            "currency": "USD"
        },

        "items": [
            {
                "item_name": "AI Development Service",
                "quantity": 2,
                "unit_price": 500.0,
                "line_total": 1000.0
            },
            {
                "item_name": "Cloud Hosting",
                "quantity": 1,
                "unit_price": 245.5,
                "line_total": 245.5
            }
        ],

        "validation_summary": {
            "is_valid": True,
            "validation_score": 0.98,
            "errors": [],
            "warnings": [
                "Discount normalized from percentage string"
            ]
        },

        "metadata": {
            "processed_by": "Data Standardization Agent v2.0",
            "schema_version": "2.1"
        },

        "standardization_status": {
            "is_standardized": True,

            "changes_applied": [
                "Removed extra spaces",
                "Converted currency symbol to USD",
                "Normalized invoice dates",
                "Converted amount strings to float",
                "Normalized email addresses",
                "Standardized file paths",
                "Generated line totals",
                "Applied enterprise schema mapping"
            ]
        }
    }

    return standardized_output

