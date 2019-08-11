from a10_octavia.db import repositories as repo
from a10_octavia.db import api as db_apis
from oslo_utils import uuidutils


class VThunderDB():
    def __init__(self, **kwargs):
        self.vthunder_repo = repo.VThunderRepository()

    def create_vthunder(self, project_id, device_name, username, password, ip_address, undercloud=None, axapi_version=30):
        if axapi_version == 2.1:
            axapi_version = 21
        else:
            axapi_version = 30

        amphora_id = uuidutils.generate_uuid()
        vthunder_id = uuidutils.generate_uuid()

        if undercloud == 'True' or undercloud == 'true':
            undercloud = True
        else:
            undercloud = False
        
        db_session = db_apis.get_session()
        vthunder = self.vthunder_repo.create(db_session, vthunder_id=vthunder_id, amphora_id=amphora_id,
                                             project_id=project_id, device_name=device_name,
                                             username=username,
                                             password=password, ip_address=ip_address,
                                             undercloud=undercloud, axapi_version=axapi_version)
        db_apis.close_session(db_session)

        print("vThunder entry created successfully.")

    def update_vthunder(self, id,  project_id, device_name, username, password, ip_address, undercloud=None, axapi_version=30):
        if axapi_version == 2.1:
            axapi_version = 21
        else:
            axapi_version = 30

        if undercloud == 'True' or undercloud == 'true':
            undercloud = True
        else:
            undercloud = False

        db_session = db_apis.get_session()
        vthunder = self.vthunder_repo.update(db_session, id, project_id=project_id, 
                                             device_name=device_name, username=username,
                                             password=password, ip_address=ip_address,
                                             undercloud=undercloud, axapi_version=axapi_version)
        db_apis.close_session(db_session)

        print("vThunder entry updated successfully.")


    def delete_vthunder(self, vthunderid):
        db_session = db_apis.get_session()
        vthunder = self.vthunder_repo.delete(db_session, id=vthunderid)
        db_apis.close_session(db_session)
        print("vThunder entry deleted successfully.")