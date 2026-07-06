"use client";

import { useState, useEffect } from "react";
import { Star, MessageCircle, ThumbsUp, Shield } from "lucide-react";

interface SocietyReviewsProps {
  propertyId: string;
}

interface ReviewData {
  overall_rating: number;
  total_reviews: number;
  categories: {
    "Safety & Security": number;
    "Maintenance": number;
    "Water & Power": number;
  };
  recent_reviews: {
    user: string;
    date: string;
    rating: number;
    text: string;
  }[];
}

export function SocietyReviews({ propertyId }: SocietyReviewsProps) {
  const [data, setData] = useState<ReviewData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`http://localhost:10000/api/properties/${propertyId}/reviews`)
      .then(res => res.json())
      .then(json => {
        if (json.status === "success") {
          setData(json.data);
        }
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch reviews", err);
        setLoading(false);
      });
  }, [propertyId]);

  if (loading) {
    return (
      <div className="bg-surface rounded-2xl border border-border-custom p-6 animate-pulse">
        <div className="h-6 w-1/3 bg-cream rounded mb-4"></div>
        <div className="h-4 w-full bg-cream rounded mb-2"></div>
        <div className="h-4 w-2/3 bg-cream rounded"></div>
      </div>
    );
  }

  if (!data) return null;

  const renderStars = (rating: number) => {
    return (
      <div className="flex gap-0.5">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            className={`w-3.5 h-3.5 ${
              star <= Math.round(rating) ? "text-warm-gold fill-warm-gold" : "text-border-custom fill-none"
            }`}
          />
        ))}
      </div>
    );
  };

  return (
    <div className="bg-surface rounded-2xl border border-border-custom p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="font-dm font-bold text-charcoal text-lg flex items-center gap-2">
          <MessageCircle className="w-5 h-5 text-forest" />
          Society Reviews
        </h3>
        <div className="flex items-center gap-1.5 px-3 py-1 bg-warm-gold/10 text-warm-gold rounded-full font-bold text-sm">
          <Star className="w-4 h-4 fill-warm-gold" /> {data.overall_rating}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-6">
        {Object.entries(data.categories).map(([category, score]) => (
          <div key={category} className="bg-cream rounded-xl p-3 border border-border-custom text-center">
            <p className="text-[10px] font-dm font-semibold text-muted uppercase tracking-wider mb-1">{category}</p>
            <p className="text-xl font-playfair text-charcoal">{score.toFixed(1)}</p>
          </div>
        ))}
      </div>

      <div className="space-y-4">
        <h4 className="text-xs font-dm font-semibold text-muted uppercase tracking-wider mb-2">Recent Resident Feedback</h4>
        {data.recent_reviews.map((review, idx) => (
          <div key={idx} className="pb-4 border-b border-border-custom last:border-0 last:pb-0">
            <div className="flex justify-between items-start mb-2">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-full bg-forest/20 flex items-center justify-center text-xs font-bold text-forest">
                  {review.user[0]}
                </div>
                <div>
                  <p className="text-xs font-dm font-bold text-charcoal">{review.user}</p>
                  <p className="text-[10px] font-dm text-muted">{review.date}</p>
                </div>
              </div>
              {renderStars(review.rating)}
            </div>
            <p className="text-sm font-dm text-charcoal leading-relaxed">{review.text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
