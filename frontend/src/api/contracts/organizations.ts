export interface OrganizationCreate {
  name: string;
}

export interface OrganizationRead {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
}
