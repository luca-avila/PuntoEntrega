export interface OrganizationCreate {
  name: string;
}

export interface OrganizationRead {
  id: string;
  name: string;
  slug: string;
  owner_user_id: string;
  is_active: boolean;
}
