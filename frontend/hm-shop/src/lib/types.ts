export type Product = {
    id: number;
    name: string;
    price: number;
    image_url: string;
    product_group_name?: string;
    description?: string;
    category?: string;
    tags?: string[];
    inStock?: boolean;
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
  