from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from lims.addressbook.models import Address
from lims.shared.loggedintestcase import LoggedInTestCase
from rest_framework import status


class UserTestCase(LoggedInTestCase):
    def setUp(self):
        super(UserTestCase, self).setUp()
        # No need to define any other users as we have them from LoggedInTestCase already
        # Add extra details to one existing user
        self._joeBloggs.first_name = "Joe"
        self._joeBloggs.last_name = "Bloggs"
        self._joeBloggsAddress = Address.objects.create(institution_name="Beetroot Institute",
                                                        address_1="12 Muddy Field",
                                                        address_2="Long Lane",
                                                        city="Norwich",
                                                        postcode="NR1 1AA",
                                                        country="UK",
                                                        user=self._joeBloggs)
        self._joeBloggs.addresses.add(self._joeBloggsAddress)
        self._joeBloggs.save()

    def test_presets(self):
        self.assertIs(User.objects.filter(username="Joe Bloggs").exists(), True)
        user1 = User.objects.get(username="Joe Bloggs")
        self.assertEqual(user1.email, "joe@tgac.com")
        self.assertEqual(user1.first_name, "Joe")
        self.assertEqual(user1.last_name, "Bloggs")
        self.assertEqual(user1.addresses.count(), 1)
        self.assertEqual(user1.addresses.all()[0], self._joeBloggsAddress)
        self.assertEqual(user1.groups.count(), 1)
        self.assertEqual(user1.groups.all()[0], Group.objects.get(name="joe_group"))
        self.assertIs(User.objects.filter(username="Jane Doe").exists(), True)
        user1 = User.objects.get(username="Jane Doe")
        self.assertEqual(user1.email, "jane@tgac.com")
        self.assertEqual(User.objects.count(), 5)  # 4 presets plus default Anonymous user

    def test_access_anonymous(self):
        self._asAnonymous()
        response = self._client.get('/users/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self._client.get('/users/%d/' % self._joeBloggs.id)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_invalid(self):
        self._asInvalid()
        response = self._client.get('/users/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self._client.get('/users/%d/' % self._joeBloggs.id)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_list(self):
        # Others not permitted
        self._asJoeBloggs()
        response = self._client.get('/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        users = response.data
        self.assertEqual(len(users["results"]), 1)
        user1 = users["results"][0]
        self.assertEqual(user1["username"], "Joe Bloggs")

    def test_user_view_own(self):
        self._asJoeBloggs()
        response = self._client.get('/users/%d/' % self._joeBloggs.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user1 = response.data
        self.assertEqual(user1["username"], "Joe Bloggs")
        self.assertEqual(user1["email"], "joe@tgac.com")
        self.assertEqual(user1["first_name"], "Joe")
        self.assertEqual(user1["last_name"], "Bloggs")
        addresses = user1["addresses"]
        self.assertEqual(len(addresses), 1)
        self.assertEqual(addresses[0]["institution_name"], "Beetroot Institute")
        groups = user1["groups"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0], "joe_group")

    def test_user_view_other(self):
        # Others not permitted
        self._asJaneDoe()
        response = self._client.get('/users/%d/' % self._janeDoe.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self._client.get('/users/%d/' % self._joeBloggs.id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_list(self):
        self._asAdmin()
        response = self._client.get('/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        users = response.data
        self.assertEqual(len(users["results"]), 5)

    def test_admin_view_any(self):
        self._asAdmin()
        response = self._client.get('/users/%d/' % self._joeBloggs.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user1 = response.data
        self.assertEqual(user1["username"], "Joe Bloggs")
        self.assertEqual(user1["email"], "joe@tgac.com")
        self.assertEqual(user1["first_name"], "Joe")
        self.assertEqual(user1["last_name"], "Bloggs")
        addresses = user1["addresses"]
        self.assertEqual(len(addresses), 1)
        self.assertEqual(addresses[0]["institution_name"], "Beetroot Institute")
        groups = user1["groups"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0], "joe_group")

    def test_user_create(self):
        self._asJaneDoe()
        new_user = {"username": "Test_User", "email": "Silly@silly.com", "password": "worms"}
        response = self._client.post("/users/", new_user, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIs(User.objects.filter(username="Test_User").exists(), False)
        self.assertEqual(User.objects.count(), 5)

    def test_admin_create(self):
        self._asAdmin()
        new_user = {"username": "Test_User",
                    "email": "Silly@silly.com",
                    "password": "worms",
                    "first_name": "Test",
                    "last_name": "User",
                    "groups": ["joe_group"]}
        response = self._client.post("/users/", new_user, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIs(User.objects.filter(username="Test_User").exists(), True)
        self.assertEqual(User.objects.count(), 6)
        user1 = User.objects.get(username="Test_User")
        self.assertEqual(user1.email, "Silly@silly.com")
        self.assertEqual(user1.first_name, "Test")
        self.assertEqual(user1.last_name, "User")
        self.assertEqual(user1.groups.count(), 2)
        self.assertEqual(set(user1.groups.all()),
                         set([Group.objects.get(name="user"), Group.objects.get(name="joe_group")]))

        # Other user still sees just theirs but we see both our old and new ones
        self._asJoeBloggs()
        response = self._client.get('/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        users = response.data
        self.assertEqual(len(users["results"]), 1)
        self._asAdmin()
        response = self._client.get('/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        users = response.data
        self.assertEqual(len(users["results"]), 6)

    def test_user_edit_own(self):
        self._asJaneDoe()
        updated_user = {"email": "onion@apple.com"}
        response = self._client.patch("/users/%d/" % self._janeDoe.id,
                                      updated_user, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user1 = User.objects.get(username="Jane Doe")
        self.assertEqual(user1.email, "onion@apple.com")

    def test_user_edit_other(self):
        # Others not permitted
        self._asJoeBloggs()
        updated_user = {"email": "onion@apple.com"}
        response = self._client.patch("/users/%d/" % self._janeDoe.id,
                                      updated_user, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        user1 = User.objects.get(username="Jane Doe")
        self.assertEqual(user1.email, "jane@tgac.com")

    def test_admin_edit_any(self):
        self._asAdmin()
        updated_user = {"email": "onion@apple.com"}
        response = self._client.patch("/users/%d/" % self._janeDoe.id,
                                      updated_user, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user1 = User.objects.get(username="Jane Doe")
        self.assertEqual(user1.email, "onion@apple.com")

    def test_user_delete_own(self):
        self._asJoeBloggs()
        response = self._client.delete("/users/%d/" % self._joeBloggs.id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIs(User.objects.filter(username="Joe Bloggs").exists(), False)

    def test_user_delete_other(self):
        # Others not permitted
        self._asJaneDoe()
        response = self._client.delete("/users/%d/" % self._joeBloggs.id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIs(User.objects.filter(username="Joe Bloggs").exists(), True)

    def test_admin_delete_any(self):
        self._asAdmin()
        response = self._client.delete("/users/%d/" % self._joeBloggs.id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIs(User.objects.filter(username="Joe Bloggs").exists(), False)

    def test_anonymous_register(self):
        self._asAnonymous()
        new_user = {"username": "Test_User",
                    "email": "Silly@silly.com",
                    "password": "worms",
                    "first_name": "Test",
                    "last_name": "User",
                    "groups": ["joe_group"]}
        response = self._client.post("/users/register/", new_user, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIs(User.objects.filter(username="Test_User").exists(), True)
        self.assertEqual(User.objects.count(), 6)
        user1 = User.objects.get(username="Test_User")
        self.assertEqual(user1.email, "Silly@silly.com")
        self.assertEqual(user1.first_name, "Test")
        self.assertEqual(user1.last_name, "User")
        self.assertEqual(user1.groups.count(), 1)
        self.assertEqual(user1.groups.all()[0], Group.objects.get(name="user"))
        self.assertEqual(user1.groups.count(), 2)
        self.assertEqual(set(user1.groups.all()),
                         set([Group.objects.get(name="user"), Group.objects.get(name="joe_group")]))

    def test_anonymous_invalid_list_staff(self):
        self._asAnonymous()
        response = self._client.get("/users/staff/", format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self._asInvalid()
        response = self._client.get("/users/staff/", format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_list_staff(self):
        self._asJoeBloggs()
        response = self._client.get("/users/staff/", format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_admin_list_staff(self):
        self._asAdmin()
        response = self._client.get("/users/staff/", format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self._janeDoe.id)

    def test_anonymous_invalid_autocomplete(self):
        query1 = {"q": "oggs"}
        self._asAnonymous()
        response = self._client.get("/users/autocomplete/", query1, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self._asInvalid()
        response = self._client.get("/users/autocomplete/", query1, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_autocomplete(self):
        query1 = {"q": "oggs"}
        self._asJoeBloggs()
        response = self._client.get("/users/autocomplete/", query1, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self._joeBloggs.id)
        self._asJaneDoe()
        response = self._client.get("/users/autocomplete/", query1, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_admin_autocomplete(self):
        query1 = {"q": "oggs"}
        self._asAdmin()
        response = self._client.get("/users/autocomplete/", query1, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self._joeBloggs.id)


class GroupTestCase(LoggedInTestCase):
    def setUp(self):
        super(GroupTestCase, self).setUp()
        # No need to define any other groups as we have them from LoggedInTestCase already
        self._janeGroup = Group.objects.get(name="jane_group")
        self._joeGroup = Group.objects.get(name="joe_group")

    def test_presets(self):
        self.assertIs(Group.objects.filter(name="joe_group").exists(), True)
        self.assertIs(Group.objects.filter(name="jane_group").exists(), True)
        self.assertEqual(Group.objects.count(), 5)  # joe, jane, user, admin, staff
        self._joeGroup = Group.objects.get(name="joe_group")
        self._janeGroup = Group.objects.get(name="jane_group")

    def test_access_anonymous(self):
        self._asAnonymous()
        response = self._client.get('/groups/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self._client.get('/groups/%d/' % self._joeGroup.id)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_invalid(self):
        self._asInvalid()
        response = self._client.get('/groups/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self._client.get('/groups/%d/' % self._joeGroup.id)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_list(self):
        self._asJoeBloggs()
        response = self._client.get('/groups/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        groups = response.data
        self.assertEqual(len(groups["results"]), 5)

    def test_user_view_any(self):
        self._asJoeBloggs()
        response = self._client.get('/groups/%d/' % self._janeGroup.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        group1 = response.data
        self.assertEqual(group1["name"], "jane_group")

    def test_admin_list(self):
        self._asAdmin()
        response = self._client.get('/groups/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        groups = response.data
        self.assertEqual(len(groups["results"]), 5)

    def test_admin_view_any(self):
        self._asAdmin()
        response = self._client.get('/groups/%d/' % self._janeGroup.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        group1 = response.data
        self.assertEqual(group1["name"], "jane_group")

    def test_user_create(self):
        self._asJaneDoe()
        new_group = {"name": "Test_Group", "permissions": ["Can change equipment"]}
        response = self._client.post("/groups/", new_group, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIs(Group.objects.filter(name="Test_Group").exists(), False)
        self.assertEqual(Group.objects.count(), 5)

    def test_admin_create(self):
        self._asAdmin()
        new_group = {"name": "Test_Group", "permissions": ["Can change equipment"]}
        response = self._client.post("/groups/", new_group, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIs(Group.objects.filter(name="Test_Group").exists(), True)
        self.assertEqual(Group.objects.count(), 6)
        group = Group.objects.get(name="Test_Group")
        self.assertEqual(set(group.permissions.all()),
                         set([Permission.objects.get(name="Can change equipment")]))

        # Other user sees the new one too
        self._asJoeBloggs()
        response = self._client.get('/groups/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        groups = response.data
        self.assertEqual(len(groups["results"]), 6)

    def test_user_edit_any(self):
        self._asJaneDoe()
        updated_group = {"permissions": ["Can change equipment"]}
        response = self._client.patch("/groups/%d/" % self._joeGroup.id,
                                      updated_group, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        group1 = Group.objects.get(name="joe_group")
        self.assertEqual(len(group1.permissions.all()), 0)

    def test_admin_edit_any(self):
        self._asAdmin()
        updated_group = {"permissions": ["Can change equipment"]}
        response = self._client.patch("/groups/%d/" % self._joeGroup.id,
                                      updated_group, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        group1 = Group.objects.get(name="joe_group")
        self.assertEqual(set(group1.permissions.all()),
                         set([Permission.objects.get(name="Can change equipment")]))

    def test_user_delete_any(self):
        self._asJoeBloggs()
        response = self._client.delete("/groups/%d/" % self._joeGroup.id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIs(Group.objects.filter(name="joe_group").exists(), True)

    def test_admin_delete_any(self):
        # Others not permitted
        self._asAdmin()
        response = self._client.delete("/groups/%d/" % self._joeGroup.id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIs(Group.objects.filter(name="joe_group").exists(), False)


class PermissionTestCase(LoggedInTestCase):
    def setUp(self):
        super(PermissionTestCase, self).setUp()
        self._changeEquipPermission = Permission.objects.get(name="Can change equipment")

    def test_presets(self):
        self.assertIs(Permission.objects.filter(name="Can change equipment").exists(), True)
        self.assertEqual(Permission.objects.get(name="Can change equipment").codename,
                         "change_equipment")

    def test_access_anonymous(self):
        self._asAnonymous()
        response = self._client.get('/permissions/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self._client.get('/permissions/%d/' % self._changeEquipPermission.id)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_invalid(self):
        self._asInvalid()
        response = self._client.get('/permissions/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self._client.get('/permissions/%d/' % self._changeEquipPermission.id)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_list(self):
        self._asJoeBloggs()
        response = self._client.get('/permissions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        permissions = response.data
        self.assertEqual(permissions["count"], Permission.objects.count())

    def test_user_view_any(self):
        self._asJoeBloggs()
        response = self._client.get('/permissions/%d/' % self._changeEquipPermission.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        permission1 = response.data
        self.assertEqual(permission1["name"], "Can change equipment")

    def test_admin_list(self):
        self._asAdmin()
        response = self._client.get('/permissions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        permissions = response.data
        self.assertEqual(permissions["count"], Permission.objects.count())

    def test_admin_view_any(self):
        self._asAdmin()
        response = self._client.get('/permissions/%d/' % self._changeEquipPermission.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        permission1 = response.data
        self.assertEqual(permission1["name"], "Can change equipment")

    def test_user_create(self):
        self._asJaneDoe()
        new_permission = {"name": "Test permission", "codename": "test_permission",
                          "content_type": ContentType.objects.get(model="equipment").id}
        response = self._client.post("/permissions/", new_permission, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIs(Permission.objects.filter(name="Test permission").exists(), False)

    def test_admin_create(self):
        self._asAdmin()
        new_permission = {"name": "Test permission", "codename": "test_permission",
                          "content_type": ContentType.objects.get(model="equipment").id}
        response = self._client.post("/permissions/", new_permission, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIs(Permission.objects.filter(name="Test permission").exists(), True)
        permission = Permission.objects.get(name="Test permission")
        self.assertEqual(permission.codename, "test_permission")
        self.assertEqual(permission.content_type, ContentType.objects.get(model="equipment"))

        # Other user sees the new one too
        self._asJoeBloggs()
        response = self._client.get('/permissions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        permissions = response.data
        self.assertEqual(len(permissions["results"]), Permission.objects.count())

    def test_user_edit_any(self):
        self._asJaneDoe()
        updated_permission = {"codename": "silly_test"}
        response = self._client.patch("/permissions/%d/" % self._changeEquipPermission.id,
                                      updated_permission, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        permission1 = Permission.objects.get(name="Can change equipment")
        self.assertEqual(permission1.codename, "change_equipment")

    def test_admin_edit_any(self):
        self._asAdmin()
        updated_permission = {"codename": "silly_test"}
        response = self._client.patch("/permissions/%d/" % self._changeEquipPermission.id,
                                      updated_permission, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        permission1 = Permission.objects.get(name="Can change equipment")
        self.assertEqual(permission1.codename, "silly_test")

    def test_user_delete_any(self):
        self._asJoeBloggs()
        response = self._client.delete("/permissions/%d/" % self._changeEquipPermission.id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIs(Permission.objects.filter(name="Can change equipment").exists(), True)

    def test_admin_delete_any(self):
        # Others not permitted
        self._asAdmin()
        response = self._client.delete("/permissions/%d/" % self._changeEquipPermission.id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIs(Permission.objects.filter(name="Can change equipment").exists(), False)
