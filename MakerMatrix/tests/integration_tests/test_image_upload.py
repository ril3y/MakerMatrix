"""
Integration tests for image upload functionality.
"""

import os
import pytest
from io import BytesIO
from PIL import Image
from fastapi.testclient import TestClient
from MakerMatrix.main import app
from MakerMatrix.database.db import engine
from MakerMatrix.models.models import PartModel, LocationModel, CategoryModel
from sqlmodel import Session, select


@pytest.fixture
def admin_token():
    """Get an admin token for authentication."""
    client = TestClient(app)
    # Login data for the admin user
    login_data = {"username": "admin", "password": "Admin123!"}

    # Post to the login endpoint
    response = client.post("/auth/login", json=login_data)

    # Check that the login was successful
    assert response.status_code == 200

    # Extract and return the access token
    return response.json()["access_token"]


class TestImageUpload:
    """Test cases for image upload and integration with parts."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        # Create upload directory if it doesn't exist
        os.makedirs("MakerMatrix/services/static/images", exist_ok=True)

        # Create test part
        with Session(engine) as session:
            # Create a test category
            category = CategoryModel(name="Test Category")
            session.add(category)
            session.commit()
            session.refresh(category)

            # Create a test location
            location = LocationModel(name="Test Location")
            session.add(location)
            session.commit()
            session.refresh(location)

            # Create a test part
            part = PartModel(
                part_name="Test Part for Image", part_number="TEST-IMG-001", quantity=10, location_id=location.id
            )
            session.add(part)
            session.commit()
            session.refresh(part)

            self.test_part_id = part.id
            self.test_category_id = category.id
            self.test_location_id = location.id

        yield

        # Cleanup
        with Session(engine) as session:
            # Delete test data
            part = session.get(PartModel, self.test_part_id)
            if part:
                session.delete(part)

            category = session.get(CategoryModel, self.test_category_id)
            if category:
                session.delete(category)

            location = session.get(LocationModel, self.test_location_id)
            if location:
                session.delete(location)

            session.commit()

        # Clean up uploaded test images
        if os.path.exists("MakerMatrix/services/static/images"):
            for file in os.listdir("MakerMatrix/services/static/images"):
                if file.startswith("test_"):
                    os.remove(os.path.join("MakerMatrix/services/static/images", file))

    def create_test_image(self, name="test_image.png"):
        """Create a test image file."""
        image = Image.new("RGB", (100, 100), color="red")
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format="PNG")
        img_byte_arr.seek(0)
        return img_byte_arr, name

    def test_upload_image_endpoint(self, admin_token):
        """Test the basic image upload endpoint."""
        client = TestClient(app)

        # Create a test image
        img_data, filename = self.create_test_image()

        # Upload the image
        response = client.post(
            "/api/utility/upload_image",
            files={"file": (filename, img_data, "image/png")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "image_id" in data

        # Verify the file was saved
        image_id = data["image_id"]
        expected_path = f"MakerMatrix/services/static/images/{image_id}.png"
        assert os.path.exists(expected_path)

        # Clean up
        os.remove(expected_path)

    def test_get_image_endpoint(self, admin_token):
        """Test retrieving an uploaded image."""
        client = TestClient(app)

        # Upload an image first
        img_data, filename = self.create_test_image()
        upload_response = client.post(
            "/api/utility/upload_image",
            files={"file": (filename, img_data, "image/png")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        image_id = upload_response.json()["image_id"]

        # Try to retrieve the image
        response = client.get(
            f"/api/utility/get_image/{image_id}.png", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

        # Clean up
        os.remove(f"MakerMatrix/services/static/images/{image_id}.png")

    def test_image_not_linked_to_part(self, admin_token):
        """Test that uploaded images are not automatically linked to parts."""
        client = TestClient(app)

        # Upload an image
        img_data, filename = self.create_test_image()
        upload_response = client.post(
            "/api/utility/upload_image",
            files={"file": (filename, img_data, "image/png")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        image_id = upload_response.json()["image_id"]

        # Check that the part doesn't have an image_url
        with Session(engine) as session:
            part = session.get(PartModel, self.test_part_id)
            assert part.image_url is None

        # Clean up
        os.remove(f"MakerMatrix/services/static/images/{image_id}.png")

    @pytest.mark.integration
    def test_update_part_with_image_url(self, admin_token):
        """Test updating a part with an image URL."""
        client = TestClient(app)

        # Upload an image first
        img_data, filename = self.create_test_image()
        upload_response = client.post(
            "/api/utility/upload_image",
            files={"file": (filename, img_data, "image/png")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        image_id = upload_response.json()["image_id"]
        image_url = f"/api/utility/get_image/{image_id}.png"

        # Update the part with the image URL
        update_data = {"image_url": image_url}

        response = client.put(
            f"/api/parts/update_part/{self.test_part_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200

        # Verify the part has the image URL
        part_response = client.get(
            f"/api/parts/get_part?part_id={self.test_part_id}", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert part_response.status_code == 200
        part_data = part_response.json()["data"]
        assert part_data["image_url"] == image_url

        # Clean up
        os.remove(f"MakerMatrix/services/static/images/{image_id}.png")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
