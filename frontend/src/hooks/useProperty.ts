import { useState, useEffect } from 'react';
import { ApiClient } from '@/lib/api-client';

export function useProperty(propertyId: string | null) {
  const [property, setProperty] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!propertyId) return;

    const fetchProperty = async () => {
      setLoading(true);
      setError(null);
      try {
        const json = await ApiClient.get(`/api/properties/${propertyId}`);
        if (json.status === "success") {
          setProperty(json.data);
        } else {
          setError(json.message || "Failed to fetch property");
        }
      } catch (err: any) {
        setError(err.message || "An error occurred");
      } finally {
        setLoading(false);
      }
    };

    fetchProperty();
  }, [propertyId]);

  return { property, loading, error };
}
