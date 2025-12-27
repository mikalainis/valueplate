package location

import (
	"context"
	"googlemaps.github.io/maps"
	"log"
)

type StoreClient struct {
	MapsClient *maps.Client
}

func (c *StoreClient) GetNearbyStores(ctx context.Context, zip string, radius int) ([]maps.PlacesSearchResult, error) {
	// 1. Geocode Zip Code to Lat/Lng
	r := &maps.GeocodingRequest{Address: zip}
	resp, err := c.MapsClient.Geocode(ctx, r)
	if err != nil || len(resp) == 0 {
		return nil, err
	}

	location := resp[0].Geometry.Location

	// 2. Search for Grocery Stores within radius (meters)
	searchReq := &maps.NearbySearchRequest{
		Location: &location,
		Radius:   uint(radius * 1609), // Miles to Meters
		Type:     maps.PlaceTypeGroceryOrSupermarket,
	}

	searchResp, err := c.MapsClient.NearbySearch(ctx, searchReq)
	return searchResp.Results, err
}