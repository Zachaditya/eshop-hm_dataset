export type Product = {
  id: string | number;
  name: string;
  price: number;
  image_url?: string | null;
  image_key?: string | null;
  product_group_name?: string;
  description?: string;
};
  
  export type Event = {
    id: string | number;
    title: string;
    startsAt?: string; // ISO
    endsAt?: string;   // ISO
    bannerUrl?: string;
  };
  
  export type Recommendation = {
    productId: string | number;
    score?: number;
    reason?: string;
  };
  